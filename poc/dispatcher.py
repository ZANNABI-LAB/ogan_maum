#!/usr/bin/env python3
"""
AI Company 디스패처 v0.2 (M0 PoC)

원칙
- LLM이 제안하고, 이 코드가 집행한다. 상태는 이 파일만 쓴다 (single writer).
- agent.finished != task.done. 에이전트 종료, CI 통과, 사람 판단은 서로 다른 상태다.
- CI 판정은 "필수 체크 2개가, 지금 PR head 커밋에서, 둘 다 success" 일 때만 VERIFIED.
  누락·skipped·cancelled·pending 은 성공이 아니다.
- 사람 판단(decide)은 검증한 SHA와 현재 PR head SHA가 같을 때만 기록된다.
- decide approve 는 장부에 HUMAN_APPROVED 로 남길 뿐이다. GitHub 리뷰 승인과 머지는 사람이 GitHub에서 따로 한다.
- 보호 경로 변경은 PR 안의 CI가 아니라 이 디스패처(신뢰된 main 체크아웃에서 실행)가 git diff로 직접 검사한다.
- Routine 접수(/fire)에는 멱등 키가 없다 → 응답이 불확실하면 자동 재시도하지 않는다.

이 파일은 반드시 깨끗한 main 체크아웃에서 실행한다. PR 브랜치 안의 디스패처를 검증기로 실행하지 않는다.

사용법 (저장소 루트에서)
  python3 poc/dispatcher.py run poc/jobs/x.md            # 로컬 경로 완주: 실행→보호검사→push→봇 PR→CI 대기→기록
  python3 poc/dispatcher.py run-local poc/jobs/x.md      # 로컬 실행 단계만
  python3 poc/dispatcher.py fire poc/jobs/x.md           # Routine 접수 (비교 실험)
  python3 poc/dispatcher.py reconcile <JOB_ID> --session-url URL | --not-found
  python3 poc/dispatcher.py open-pr <JOB_ID>             # 봇으로 PR 생성 (있으면 재사용)
  python3 poc/dispatcher.py check <JOB_ID> [--wait]      # CI 판정 기록
  python3 poc/dispatcher.py decide <JOB_ID> approve|reject --reason "..."
  python3 poc/dispatcher.py status [--json]

환경 변수
  CLAUDE_BIN        claude 실행 파일 (기본: claude). 본인 구독으로 로그인되어 있어야 함
  BOT_GH_TOKEN      PR을 여는 봇 토큰 (내 계정 토큰 X)
  BOT_GH_TOKEN_CMD  호출할 때마다 새 봇 토큰을 출력하는 명령 (GitHub App 설치 토큰은 1시간 만료 → 이쪽 권장)
  ROUTINE_URL, ROUTINE_TOKEN   Routine 비교 실험용
  CI_TIMEOUT_S (기본 1200), CI_POLL_S (기본 30)
"""
import argparse, datetime as dt, json, os, shlex, sqlite3, subprocess, sys, time, uuid
import urllib.error, urllib.request
from pathlib import Path

# ---- 예산 (구독 잔량 조회 API가 없으므로 횟수로 제한) ----
MAX_JOBS_PER_DAY = 10
MAX_CONCURRENT = 2
LOCAL_MAX_TURNS = 40
BASE_BRANCH = "main"

# ---- 보호 경로: 프롬프트, CI, CODEOWNERS, 디스패처 검사 모두 이 목록과 같아야 한다 ----
PROTECTED_PREFIXES = ("test/acceptance/", "poc/", ".github/")
PROTECTED_FILES = ("analysis_options.yaml", "CODEOWNERS")

# ---- 필수 CI 체크 (verify.yml 의 job name) 와 신뢰하는 출처 ----
REQUIRED_CHECKS = ("analyze-and-test", "protected-paths")
TRUSTED_APP_SLUG = "github-actions"
TRUSTED_WORKFLOW_PATH = ".github/workflows/verify.yml"
TRUSTED_EVENT = "pull_request"

# ---- Claude 자식 프로세스에서 제거할 환경 변수 (집행용 비밀정보, API 키) ----
SCRUB_ENV = ("BOT_GH_TOKEN", "BOT_GH_TOKEN_CMD", "ROUTINE_TOKEN", "ROUTINE_URL",
             "GH_TOKEN", "GITHUB_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

ROOT = Path(__file__).resolve().parent.parent
POC = ROOT / "poc"
DB = POC / "ledger.db"
RUNS = POC / "runs"

ACTIVE = ("RUNNING", "SUBMITTING", "SUBMITTED", "SUBMIT_UNKNOWN", "PR_OPEN")

# --allowedTools 는 "승인 없이 실행해도 되는 도구" 목록이다. 도구 제공 범위 자체를 막는 설정이 아니며,
# 파일 쓰기를 경로 단위로 차단하지도 않는다. 실제 보호는 실행 후 protected_changes() 검사가 한다.
ALLOWED_TOOLS = ",".join([
    "Read", "Edit", "Write", "Glob", "Grep",
    "Bash(flutter pub get)", "Bash(flutter analyze:*)", "Bash(flutter test:*)",
    "Bash(dart format:*)", "Bash(git status:*)", "Bash(git diff:*)",
    "Bash(git add:*)", "Bash(git commit:*)", "Bash(git log:*)",
])
RULES = """
[디스패처 규칙 — 작업지시서보다 우선]
- 다음 경로는 수정하지 않는다: test/acceptance/, poc/, .github/, analysis_options.yaml, CODEOWNERS
  (수정하면 디스패처 검사에서 NEEDS_HUMAN 으로 멈춘다)
- 완료 전 실행: dart format --output=none --set-exit-if-changed lib test / flutter analyze / flutter test
- 커밋 메시지 첫 줄에 [{job_id}] 를 붙이고 현재 브랜치에 커밋만 한다. push와 PR 생성은 하지 않는다.
- 막히면 우회하지 말고 이유를 적고 멈춘다.
- 마지막 메시지 형식:
  RESULT: success | blocked | failed
  JOB_ID: {job_id}
  SUMMARY: <한두 문장>
"""


class GhError(Exception):
    """인증·네트워크·조회 오류. 검증 실패와 구분한다."""


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def db():
    POC.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS jobs(
      job_id TEXT PRIMARY KEY, title TEXT, job_file TEXT, path TEXT,
      status TEXT NOT NULL, session_id TEXT, session_url TEXT, branch TEXT,
      pr_url TEXT, verify_sha TEXT, created_at TEXT, updated_at TEXT, note TEXT);
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY, job_id TEXT, ts TEXT, kind TEXT, payload TEXT);
    CREATE TABLE IF NOT EXISTS decisions(
      id INTEGER PRIMARY KEY, job_id TEXT, ts TEXT, verdict TEXT, reason TEXT NOT NULL, sha TEXT);
    """)
    # 이전 버전 장부 호환
    for table, col in (("decisions", "sha"), ("decisions", "evidence"), ("jobs", "verify_evidence")):
        if col not in [r[1] for r in con.execute(f"PRAGMA table_info({table})")]:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
    return con


def set_status(con, job_id, status, **fields):
    with con:  # 상태 변경과 이벤트를 한 트랜잭션으로
        cols = "".join(f", {k}=?" for k in fields)
        con.execute(f"UPDATE jobs SET status=?, updated_at=?{cols} WHERE job_id=?",
                    [status, now(), *fields.values(), job_id])
        con.execute("INSERT INTO events(job_id, ts, kind, payload) VALUES(?,?,?,?)",
                    (job_id, now(), status, json.dumps(fields, ensure_ascii=False)))


def log_event(con, job_id, kind, payload):
    with con:
        con.execute("INSERT INTO events(job_id, ts, kind, payload) VALUES(?,?,?,?)",
                    (job_id, now(), kind, json.dumps(payload, ensure_ascii=False)))


def get(con, job_id):
    row = con.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    if not row:
        sys.exit(f"없는 JOB_ID: {job_id}")
    return row


def budget_check(con):
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    n_today = con.execute("SELECT COUNT(*) FROM jobs WHERE substr(created_at,1,10)=?", (today,)).fetchone()[0]
    n_active = con.execute(f"SELECT COUNT(*) FROM jobs WHERE status IN ({','.join('?'*len(ACTIVE))})", ACTIVE).fetchone()[0]
    if n_today >= MAX_JOBS_PER_DAY:
        sys.exit(f"예산 초과: 오늘 이미 {n_today}건 접수 (상한 {MAX_JOBS_PER_DAY})")
    if n_active >= MAX_CONCURRENT:
        sys.exit(f"동시 진행 상한: {n_active}건 (상한 {MAX_CONCURRENT}). SUBMIT_UNKNOWN 은 reconcile, PR_OPEN 은 check 하세요.")


def new_job(con, job_file, path):
    text = Path(job_file).read_text(encoding="utf-8")
    title = next((l.lstrip("# ").strip() for l in text.splitlines() if l.strip()), "untitled")
    job_id = dt.datetime.now().strftime("j%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    with con:
        con.execute("INSERT INTO jobs(job_id,title,job_file,path,status,branch,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (job_id, title, str(job_file), path, "CREATED", f"claude/{job_id}", now(), now()))
    return job_id, text


def git(*args, cwd=ROOT, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True).stdout.strip()


def has_commit(sha):
    return subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=ROOT,
                          capture_output=True).returncode == 0


def trusted_protected_check(branch, sha):
    """보호 경로 검사. 커밋을 로컬에서 볼 수 없으면 None (= 판정 불가)."""
    if not has_commit(sha):
        subprocess.run(["git", "fetch", "origin", branch], cwd=ROOT, capture_output=True)
    if not has_commit(sha):
        return None
    return protected_changes(sha)


def is_protected(path):
    return path.startswith(PROTECTED_PREFIXES) or path in PROTECTED_FILES or path.endswith("/CODEOWNERS")


def protected_changes(head, base=None):
    """신뢰된 디스패처가 직접 계산하는 보호 경로 변경 목록 (브랜치 이름과 무관)."""
    base = base or BASE_BRANCH
    mb = git("merge-base", base, head, check=False) or base
    files = git("diff", "--name-only", f"{mb}..{head}", check=False).splitlines()
    return [f for f in files if is_protected(f)]


def child_env():
    env = {k: v for k, v in os.environ.items() if k not in SCRUB_ENV}
    return env


# ---------------- GitHub (봇 토큰, 오류 분리) ----------------
def bot_token():
    cmd = os.environ.get("BOT_GH_TOKEN_CMD")
    if cmd:  # 호출할 때마다 새 토큰 (App 설치 토큰 1시간 만료 대응)
        r = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            raise GhError(f"BOT_GH_TOKEN_CMD 실패: {r.stderr.strip()[:200]}")
        return r.stdout.strip()
    tok = os.environ.get("BOT_GH_TOKEN")
    if not tok:
        raise GhError("BOT_GH_TOKEN 또는 BOT_GH_TOKEN_CMD 가 필요합니다. 내 계정 토큰으로 PR을 열면 내가 승인할 수 없습니다.")
    return tok


def gh(args):
    """check=True 를 쓰지 않는다. 반환 코드를 직접 해석한다."""
    env = dict(os.environ); env["GH_TOKEN"] = bot_token()
    r = subprocess.run(["gh", *args], cwd=ROOT, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def gh_ok(args):
    rc, out, err = gh(args)
    if rc != 0:
        raise GhError(f"gh {' '.join(args[:3])} 실패 (rc={rc}): {err[:300]}")
    return out


def pr_head_sha(pr_url):
    out = gh_ok(["pr", "view", pr_url, "--json", "headRefOid,state"])
    d = json.loads(out)
    return d["headRefOid"], d.get("state")


def evaluate_checks(head_sha):
    """필수 체크를 head_sha 기준으로, 신뢰하는 출처에 한해 판정.
    반환: (verdict, detail, evidence)
      verdict: PASS | PENDING | FAIL | PROTECTED_FAIL | INCOMPLETE | UNCERTAIN
      evidence: {check name: {id, url, conclusion, check_suite_id}}  (판단 기록용)
    신뢰 조건: app.slug == github-actions, check_suite 가 이 SHA의 verify.yml(pull_request) 워크플로 실행에 속함.
    전체 조회(페이지네이션)를 확정할 수 없으면 UNCERTAIN → VERIFIED 금지.
    """
    runs, ok1, pend1 = gh_paginate(f"repos/{{owner}}/{{repo}}/commits/{head_sha}/check-runs?filter=all", "check_runs")
    wruns, ok2, pend2 = gh_paginate(f"repos/{{owner}}/{{repo}}/actions/runs?head_sha={head_sha}", "workflow_runs")
    if pend1 or pend2:
        return "PENDING", {"note": "gh rc=8"}, {}
    if not (ok1 and ok2):
        return "UNCERTAIN", {"note": "pagination incomplete", "check_runs": len(runs), "workflow_runs": len(wruns)}, {}
    trusted_suites = {w.get("check_suite_id") for w in wruns
                      if (w.get("path") or "").split("@")[0] == TRUSTED_WORKFLOW_PATH
                      and w.get("event") == TRUSTED_EVENT and w.get("head_sha") == head_sha}
    latest, ignored = {}, 0
    for run in runs:
        name = run.get("name")
        if name not in REQUIRED_CHECKS:
            continue
        suite = (run.get("check_suite") or {}).get("id")
        trusted = (run.get("head_sha") == head_sha
                   and (run.get("app") or {}).get("slug") == TRUSTED_APP_SLUG
                   and suite in trusted_suites)
        if not trusted:
            ignored += 1  # 이름·SHA가 같아도 출처가 다르면 무시
            continue
        if name not in latest or run.get("id", 0) > latest[name].get("id", 0):
            latest[name] = run  # 신뢰 출처 안에서 최신 재실행
    detail = {n: (latest[n].get("status"), latest[n].get("conclusion")) if n in latest else ("missing", None)
              for n in REQUIRED_CHECKS}
    detail["ignored_untrusted"] = ignored
    evidence = {n: {"id": r.get("id"), "url": r.get("html_url") or r.get("details_url"),
                    "conclusion": r.get("conclusion"), "check_suite_id": (r.get("check_suite") or {}).get("id")}
                for n, r in latest.items()}
    if any(n not in latest or latest[n].get("status") != "completed" for n in REQUIRED_CHECKS):
        return "PENDING", detail, evidence
    conc = {n: latest[n].get("conclusion") for n in REQUIRED_CHECKS}
    if conc["protected-paths"] == "failure":
        return "PROTECTED_FAIL", detail, evidence
    if all(c == "success" for c in conc.values()):
        return "PASS", detail, evidence
    if any(c in ("failure", "timed_out", "action_required", "startup_failure") for c in conc.values()):
        return "FAIL", detail, evidence
    return "INCOMPLETE", detail, evidence  # skipped, cancelled, neutral, stale


def gh_paginate(endpoint, key, per_page=100, max_pages=20):
    """반환: (items, complete, pending). complete=False 면 전체 조회를 확정하지 못한 것."""
    items, total = [], None
    sep = "&" if "?" in endpoint else "?"
    for page in range(1, max_pages + 1):
        rc, out, err = gh(["api", f"{endpoint}{sep}per_page={per_page}&page={page}"])
        if rc == 8:
            return items, False, True
        if rc != 0:
            raise GhError(f"{key} 조회 실패 (rc={rc}): {err[:300]}")
        data = json.loads(out or "{}")
        batch = data.get(key, [])
        total = data.get("total_count", total)
        items.extend(batch)
        if len(batch) < per_page:
            break
    else:
        return items, False, False  # max_pages 초과
    complete = total is None or len(items) >= total
    return items, complete, False


# ---------------- run-local ----------------
def run_local(con, job_file, push=True):
    budget_check(con)
    job_id, text = new_job(con, job_file, "local")
    branch = f"claude/{job_id}"
    wt = ROOT.parent / f"wt-{job_id}"
    base_sha = git("rev-parse", BASE_BRANCH)
    git("worktree", "add", str(wt), "-b", branch, BASE_BRANCH)
    run_dir = RUNS / job_id; run_dir.mkdir(parents=True, exist_ok=True)
    versions = tool_versions()
    log_event(con, job_id, "RUN_CONTEXT", {"base_sha": base_sha, "versions": versions})
    session_id = str(uuid.uuid4())
    prompt = f"JOB_ID: {job_id}\n\n{text}\n{RULES.format(job_id=job_id)}"
    cmd = [os.environ.get("CLAUDE_BIN", "claude"), "-p", prompt,
           "--output-format", "stream-json", "--verbose",
           "--session-id", session_id,
           "--permission-mode", "acceptEdits",
           "--allowedTools", ALLOWED_TOOLS,
           "--max-turns", str(LOCAL_MAX_TURNS)]
    set_status(con, job_id, "RUNNING", session_id=session_id, note=str(wt))
    print(f"[{job_id}] 실행 시작 · worktree={wt} · session={session_id}")
    result, started = None, time.time()
    log = open(run_dir / "stream.jsonl", "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=wt, env=child_env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for line in proc.stdout:
            log.write(line); log.flush()
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "result":
                result = ev
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        dirty = bool(git("status", "--porcelain", cwd=wt, check=False))
        set_status(con, job_id, "INTERRUPTED", note=f"user interrupt; dirty={dirty}")
        print(f"[{job_id}] 중단됨. 재개하려면 worktree에서: claude --resume {session_id}")
        return job_id, False
    finally:
        log.close()
    (run_dir / "stderr.txt").write_text(proc.stderr.read() if proc.stderr else "", encoding="utf-8")

    dirty = bool(git("status", "--porcelain", cwd=wt, check=False))
    base = git("merge-base", "HEAD", BASE_BRANCH, cwd=wt, check=False) or "HEAD"
    ahead = git("rev-list", "--count", f"{base}..HEAD", cwd=wt, check=False)
    head = git("rev-parse", "HEAD", cwd=wt, check=False)
    summary = {
        "exit_code": proc.returncode, "result_seen": result is not None,
        "is_error": (result or {}).get("is_error"), "subtype": (result or {}).get("subtype"),
        "num_turns": (result or {}).get("num_turns"), "duration_s": round(time.time() - started),
        "dirty_worktree": dirty, "new_commits": ahead, "head_sha": head,
        "base_sha": base_sha, "versions": versions,
        "final_text_tail": str((result or {}).get("result", ""))[-400:],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    ok = (result is not None and result.get("is_error") is False
          and result.get("subtype") == "success" and not dirty and ahead not in ("", "0"))
    if not ok:
        set_status(con, job_id, "AGENT_FAILED", note=json.dumps({k: summary[k] for k in ("is_error", "subtype", "dirty_worktree", "new_commits")}))
        print(f"[{job_id}] AGENT_FAILED → 다음 단계로 진행하지 않음")
        return job_id, False

    prot = protected_changes(head)
    if prot:
        set_status(con, job_id, "NEEDS_HUMAN", note=f"protected paths changed: {prot}")
        print(f"[{job_id}] 보호 경로 변경 감지 → NEEDS_HUMAN, 자동 처리 중단: {prot}")
        return job_id, False

    set_status(con, job_id, "AGENT_DONE")
    print(f"[{job_id}] AGENT_DONE (완료 아님)")
    if push:
        r = subprocess.run(["git", "push", "-u", "origin", branch], cwd=wt, capture_output=True, text=True)
        if r.returncode != 0:
            set_status(con, job_id, "PUSH_FAILED", note=r.stderr.strip()[:300])
            print(f"[{job_id}] push 실패: {r.stderr.strip()[:300]}")
            return job_id, False
        set_status(con, job_id, "PUSHED")
        print(f"[{job_id}] push 완료: {branch}")
    return job_id, True


def cmd_run_local(a):
    run_local(db(), a.job_file, push=not a.no_push)


# ---------------- PR / CI / 판단 ----------------
def open_pr(con, job_id):
    row = get(con, job_id)
    branch = row["branch"]
    # 기존 PR 재사용 (중복 생성 방지)
    out = gh_ok(["pr", "list", "--head", branch, "--state", "open", "--json", "url"])
    existing = json.loads(out or "[]")
    if existing:
        url = existing[0]["url"]
        print(f"[{job_id}] 기존 PR 재사용: {url}")
        if row["pr_url"] == url:  # 이미 기록된 PR이면 상태를 되돌리지 않는다
            return url
    else:
        body = (f"JOB_ID: {job_id}\npath: {row['path']}\nsession: {row['session_url'] or row['session_id']}\n"
                f"job: {row['job_file']}\n\n자동 머지·자동 배포 없음. 사람 판단 필요.")
        url = gh_ok(["pr", "create", "--head", branch, "--base", BASE_BRANCH,
                     "--title", f"[{job_id}] {row['title']}", "--body", body]).splitlines()[-1]
        print(f"[{job_id}] PR 생성: {url}")
    set_status(con, job_id, "PR_OPEN", pr_url=url)
    return url


def cmd_open_pr(a):
    con = db()
    try:
        open_pr(con, a.job_id)
    except GhError as e:
        log_event(con, a.job_id, "GH_ERROR", {"op": "open-pr", "error": str(e)})
        sys.exit(f"[{a.job_id}] GitHub 오류(검증 실패 아님): {e}")


def check_once(con, job_id):
    """한 번 판정. 반환: 최종 상태 문자열 또는 'PENDING' / 'CHECK_ERROR'."""
    row = get(con, job_id)
    if not row["pr_url"]:
        sys.exit("PR이 아직 없습니다.")
    try:
        head, state = pr_head_sha(row["pr_url"])
        verdict, detail, evidence = evaluate_checks(head)
        head_after, _ = pr_head_sha(row["pr_url"])  # 판정 도중 head 변경 방지
    except GhError as e:
        log_event(con, job_id, "CHECK_ERROR", {"error": str(e)})
        print(f"[{job_id}] 조회 오류(검증 실패 아님): {e}")
        return "CHECK_ERROR"
    if head_after != head:
        log_event(con, job_id, "HEAD_MOVED", {"from": head, "to": head_after})
        return "PENDING"
    print(f"[{job_id}] head={head[:10]} {json.dumps(detail, ensure_ascii=False)} → {verdict}")
    if verdict == "PENDING":
        return "PENDING"
    if verdict == "UNCERTAIN":
        log_event(con, job_id, "CHECK_ERROR", {"error": "check results incomplete", "detail": detail})
        print(f"[{job_id}] 체크 전체 조회를 확정할 수 없음 → 판정 보류")
        return "CHECK_ERROR"
    prot = trusted_protected_check(row["branch"], head)
    if prot is None:
        log_event(con, job_id, "CHECK_ERROR", {"error": f"trusted check unavailable: {head} not fetchable"})
        print(f"[{job_id}] 신뢰된 보호 경로 검사 불가(커밋 {head[:10]} 없음) → 판정 보류")
        return "CHECK_ERROR"
    if verdict == "PASS" and prot:
        set_status(con, job_id, "NEEDS_HUMAN", verify_sha=head, note=f"trusted check: protected paths {prot}")
        return "NEEDS_HUMAN"
    mapping = {"PASS": "VERIFIED", "FAIL": "VERIFY_FAILED", "PROTECTED_FAIL": "NEEDS_HUMAN", "INCOMPLETE": "VERIFY_INCOMPLETE"}
    status = mapping[verdict]
    set_status(con, job_id, status, verify_sha=head, verify_evidence=json.dumps(evidence),
               note=json.dumps(detail))
    return status


def check_wait(con, job_id):
    timeout = int(os.environ.get("CI_TIMEOUT_S", "1200"))
    poll = int(os.environ.get("CI_POLL_S", "30"))
    deadline = time.time() + timeout
    errors = 0
    while True:
        s = check_once(con, job_id)
        if s not in ("PENDING", "CHECK_ERROR"):
            return s
        errors = errors + 1 if s == "CHECK_ERROR" else 0
        if errors >= 3:
            set_status(con, job_id, "CHECK_ERROR", note="3회 연속 조회 오류")
            return "CHECK_ERROR"
        if time.time() + poll > deadline:
            set_status(con, job_id, "VERIFY_TIMEOUT", note=f"{timeout}s 초과")
            return "VERIFY_TIMEOUT"
        time.sleep(poll)


def cmd_check(a):
    con = db()
    s = check_wait(con, a.job_id) if a.wait else check_once(con, a.job_id)
    print(f"[{a.job_id}] → {s}")


def cmd_run(a):
    """로컬 경로 완주. 사람 판단 직전에서 멈춘다. 자동 머지·배포 없음."""
    con = db()
    job_id, ok = run_local(con, a.job_file, push=True)
    if not ok:
        return
    try:
        bot_token()  # PR 단계 전에 토큰 확인
        open_pr(con, job_id)
    except GhError as e:
        set_status(con, job_id, "PR_FAILED", note=str(e)[:300])
        print(f"[{job_id}] PR 단계 실패(GitHub 오류): {e}")
        return
    s = check_wait(con, job_id)
    print(f"\n[{job_id}] 최종 상태: {s}")
    if s == "VERIFIED":
        print("→ 사람 판단 대기. GitHub에서 리뷰 후:\n"
              f"  python3 poc/dispatcher.py decide {job_id} approve --reason \"...\"")


def cmd_decide(a):
    con = db(); row = get(con, a.job_id)
    reason = a.reason.strip()
    if not reason:
        sys.exit("--reason 은 필수입니다. 판단 이유가 판정 기준의 원재료입니다.")
    sha = row["verify_sha"]
    evidence = json.loads(row["verify_evidence"] or "{}")  # reject 는 마지막 검증 근거를 기록
    if a.verdict == "approve":
        if row["status"] != "VERIFIED":
            sys.exit(f"승인은 VERIFIED 에서만 가능 (현재 {row['status']}).")
        try:
            current, state = pr_head_sha(row["pr_url"])
        except GhError as e:
            sys.exit(f"PR head 재조회 실패 → 승인 보류: {e}")
        if current != sha:
            set_status(con, a.job_id, "PR_OPEN", note=f"head changed {sha[:10]}→{current[:10]}; 재검증 필요")
            sys.exit(f"검증 SHA({sha[:10]})와 현재 PR head({current[:10]})가 다릅니다 → 승인 거부. check 로 재검증하세요.")
        # 같은 SHA라도 CI가 재실행됐을 수 있다 → 최신 결과·출처를 다시 확인
        try:
            verdict, detail, evidence = evaluate_checks(current)
        except GhError as e:
            sys.exit(f"체크 재조회 실패 → 승인 보류: {e}")
        if verdict != "PASS":
            back = {"FAIL": "VERIFY_FAILED", "PROTECTED_FAIL": "NEEDS_HUMAN",
                    "INCOMPLETE": "VERIFY_INCOMPLETE"}.get(verdict, "PR_OPEN")
            set_status(con, a.job_id, back, note=f"pre-approval recheck: {verdict} {json.dumps(detail)}")
            sys.exit(f"승인 직전 재확인 결과 {verdict} → 승인 거부 (상태 {back}). {json.dumps(detail, ensure_ascii=False)}")
        prot = trusted_protected_check(row["branch"], current)
        if prot is None:
            sys.exit(f"커밋 {current[:10]} 를 로컬에서 볼 수 없어 보호 경로 검사 불가 → 승인 보류")
        if prot:
            set_status(con, a.job_id, "NEEDS_HUMAN", note=f"protected paths {prot}")
            sys.exit(f"보호 경로 변경이 있어 자동 승인 대상이 아닙니다: {prot}")
    with con:
        con.execute("INSERT INTO decisions(job_id, ts, verdict, reason, sha, evidence) VALUES(?,?,?,?,?,?)",
                    (a.job_id, now(), a.verdict, reason, sha, json.dumps(evidence, ensure_ascii=False)))
    set_status(con, a.job_id, "HUMAN_APPROVED" if a.verdict == "approve" else "REJECTED", note=reason)
    print(f"[{a.job_id}] {a.verdict} 기록 (sha={(sha or '')[:10]}, checks={[v.get('id') for v in evidence.values()]})")
    print("  이 기록은 지금 시점의 사람 판단이다. GitHub 리뷰 승인·머지는 GitHub에서 따로 하고, "
          "머지 시점의 필수 체크를 대체하지 않는다.")


# ---------------- Routine (비교 실험) ----------------
def cmd_fire(a):
    url, token = os.environ.get("ROUTINE_URL"), os.environ.get("ROUTINE_TOKEN")
    if not url or not token:
        sys.exit("ROUTINE_URL, ROUTINE_TOKEN 환경 변수가 필요합니다.")
    con = db(); budget_check(con)
    job_id, text = new_job(con, a.job_file, "routine")
    payload = f"JOB_ID: {job_id}\n\n{text}"
    set_status(con, job_id, "SUBMITTING")  # 요청 전에 먼저 기록
    req = urllib.request.Request(url, method="POST",
        data=json.dumps({"text": payload}).encode(),
        headers={"Authorization": f"Bearer {token}", "anthropic-version": "2023-06-01",
                 "anthropic-beta": "experimental-cc-routine-2026-04-01",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read())
        set_status(con, job_id, "SUBMITTED", session_id=body.get("claude_code_session_id"),
                   session_url=body.get("claude_code_session_url"))
        print(f"[{job_id}] 접수됨 → {body.get('claude_code_session_url')}")
        print(f"   브랜치 claude/{job_id} 가 push 되면: open-pr {job_id} → check {job_id} --wait")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        if e.code in (400, 401, 403, 404, 429):
            set_status(con, job_id, "SUBMIT_FAILED", note=f"HTTP {e.code} {detail}")
            print(f"[{job_id}] 접수 실패 HTTP {e.code}: {detail}")
        else:
            set_status(con, job_id, "SUBMIT_UNKNOWN", note=f"HTTP {e.code} {detail}")
            print(f"[{job_id}] 접수 불확실(HTTP {e.code}). 자동 재시도 안 함 → 세션 확인 후 reconcile")
    except (urllib.error.URLError, TimeoutError) as e:
        set_status(con, job_id, "SUBMIT_UNKNOWN", note=repr(e))
        print(f"[{job_id}] 접수 불확실({e}). 자동 재시도 안 함 → claude.ai/code 에서 '{job_id}' 세션 확인 후 reconcile")


def cmd_reconcile(a):
    con = db(); row = get(con, a.job_id)
    if row["status"] != "SUBMIT_UNKNOWN":
        sys.exit(f"reconcile 대상 아님 (현재 {row['status']})")
    if a.not_found:
        set_status(con, a.job_id, "SUBMIT_FAILED", note="reconciled: session not found")
    else:
        set_status(con, a.job_id, "SUBMITTED", session_url=a.session_url, note="reconciled")
    print(f"[{a.job_id}] → {get(con, a.job_id)['status']}")


def cmd_adopt(a):
    """이미 push된 브랜치를 장부에 등록 (GitHub 연결 확인용, Claude 실행 없음)."""
    con = db()
    if subprocess.run(["git", "ls-remote", "--exit-code", "origin", f"refs/heads/{a.branch}"],
                      cwd=ROOT, capture_output=True).returncode != 0:
        sys.exit(f"원격에 브랜치가 없습니다: {a.branch}")
    job_id = dt.datetime.now().strftime("a%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
    with con:
        con.execute("INSERT INTO jobs(job_id,title,job_file,path,status,branch,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (job_id, a.title, "", "adopted", "PUSHED", a.branch, now(), now()))
    print(f"[{job_id}] 등록: {a.branch} → open-pr {job_id} → check {job_id} --wait")


def tool_versions():
    out = {}
    for name, cmd in (("claude", [os.environ.get("CLAUDE_BIN", "claude"), "--version"]), ("gh", ["gh", "--version"]),
                      ("git", ["git", "--version"])):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, env=child_env())
            out[name] = (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else f"rc={r.returncode}"
        except Exception as e:
            out[name] = f"unavailable: {e.__class__.__name__}"
    return out


def cmd_status(a):
    con = db()
    rows = [dict(r) for r in con.execute(
        "SELECT job_id,status,path,title,verify_sha,pr_url,updated_at FROM jobs ORDER BY created_at DESC LIMIT 30")]
    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2)); return
    for r in rows:
        print(f"{r['job_id']:<26} {r['status']:<17} {r['path']:<8} {(r['verify_sha'] or '')[:8]:<9} {r['title'][:36]}")
    d = con.execute("SELECT verdict, COUNT(*) FROM decisions GROUP BY verdict").fetchall()
    if d:
        print("판단 기록:", ", ".join(f"{v}={n}" for v, n in d))


def main():
    ap = argparse.ArgumentParser(description="AI Company dispatcher v0.2")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("run"); p.add_argument("job_file"); p.set_defaults(f=cmd_run)
    p = sp.add_parser("run-local"); p.add_argument("job_file"); p.add_argument("--no-push", action="store_true"); p.set_defaults(f=cmd_run_local)
    p = sp.add_parser("fire"); p.add_argument("job_file"); p.set_defaults(f=cmd_fire)
    p = sp.add_parser("reconcile"); p.add_argument("job_id")
    g = p.add_mutually_exclusive_group(required=True); g.add_argument("--session-url"); g.add_argument("--not-found", action="store_true")
    p.set_defaults(f=cmd_reconcile)
    p = sp.add_parser("open-pr"); p.add_argument("job_id"); p.set_defaults(f=cmd_open_pr)
    p = sp.add_parser("check"); p.add_argument("job_id"); p.add_argument("--wait", action="store_true"); p.set_defaults(f=cmd_check)
    p = sp.add_parser("decide"); p.add_argument("job_id"); p.add_argument("verdict", choices=["approve", "reject"])
    p.add_argument("--reason", required=True); p.set_defaults(f=cmd_decide)
    p = sp.add_parser("adopt"); p.add_argument("branch"); p.add_argument("--title", default="GitHub 연결 확인")
    p.set_defaults(f=cmd_adopt)
    p = sp.add_parser("status"); p.add_argument("--json", action="store_true"); p.set_defaults(f=cmd_status)
    a = ap.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
