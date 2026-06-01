import os
import time
import sqlite3
import warnings
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.models.message import Message
from tools.recommend_tool import recommend_food
from tools.reserve_tool import reserve_food

warnings.filterwarnings("ignore")


def load_environment():
    try:
        load_dotenv(encoding="utf-8-sig")
    except UnicodeDecodeError:
        load_dotenv(encoding="utf-16")


load_environment()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not set. Create a .env file in the project root "
        "and add: OPENROUTER_API_KEY=your-key-here"
    )

MODEL_NAME = "openai/gpt-4o-mini"
AGENT_TEMPERATURE = 0.3
WITH_TOOLS_MODE = "tool"
WITHOUT_TOOLS_MODE = "no_tool"
WITH_TOOLS_LABEL = "tool"
WITHOUT_TOOLS_LABEL = "no_tool"

model = OpenAILike(
    id=MODEL_NAME,
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=AGENT_TEMPERATURE,
)

SYSTEM_PROMPT = """You are a food ordering assistant.
- Recommend food based on user preferences
- Filter food by budget, calories, and preferences
- Create food orders when requested
- Use tools to provide accurate results
Respond in the same language the user is using."""

# ─────
agent_with_tools = Agent(
    name="Food Agent With Tools",
    model=model,
    instructions=SYSTEM_PROMPT,
    tools=[recommend_food, reserve_food],
)

agent_no_tools = Agent(
    name="Food Agent No Tools",
    model=model,
    instructions=SYSTEM_PROMPT,
    tools=[],
)

# ──────
BASE_TEST_INPUT = "غذای گیاهی میخوام، بودجه‌ام ۲۵۰ هزار تومنه"
WITH_TOOLS_TEST_INPUT = (
    f"{BASE_TEST_INPUT}\n"
    "برای پاسخ دادن حتما از ابزار recommend_food استفاده کن. "
    "اگر کاربر غذا را قطعی سفارش داد، فقط آن وقت از reserve_food استفاده کن."
)
WITHOUT_TOOLS_TEST_INPUT = (
    f"{BASE_TEST_INPUT}\n"
    "بدون استفاده از ابزار پاسخ بده و فقط بر اساس دانش خودت پیشنهاد بده."
)

NUM_RUNS = 20


def setup_database() -> tuple[sqlite3.Connection, Path]:
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    db_path = logs_dir / "benchmark_results.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            test_input TEXT NOT NULL,
            with_tools_input TEXT NOT NULL,
            without_tools_input TEXT NOT NULL,
            num_runs INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            temperature REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            agent_label TEXT NOT NULL,
            agent_mode TEXT NOT NULL,
            run_number INTEGER NOT NULL,
            input TEXT NOT NULL,
            output TEXT NOT NULL,
            elapsed_seconds REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES benchmark_sessions (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_averages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL UNIQUE,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            test_input TEXT NOT NULL,
            with_tools_input TEXT NOT NULL,
            without_tools_input TEXT NOT NULL,
            num_runs INTEGER NOT NULL,
            model_name TEXT NOT NULL,
            temperature REAL NOT NULL,
            with_tools_average_seconds REAL NOT NULL,
            with_tools_min_seconds REAL NOT NULL,
            with_tools_max_seconds REAL NOT NULL,
            without_tools_average_seconds REAL NOT NULL,
            without_tools_min_seconds REAL NOT NULL,
            without_tools_max_seconds REAL NOT NULL,
            average_diff_seconds REAL NOT NULL,
            faster_agent TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES benchmark_sessions (id)
        )
    """)
    ensure_column(conn, "benchmark_sessions", "temperature", "REAL NOT NULL DEFAULT 0.3")
    ensure_column(conn, "benchmark_averages", "temperature", "REAL NOT NULL DEFAULT 0.3")
    conn.commit()

    return conn, db_path


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_definition: str):
    columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    if column_name not in [column["name"] for column in columns]:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def create_benchmark_session(conn: sqlite3.Connection) -> int:
    cur = conn.execute("""
        INSERT INTO benchmark_sessions (
            started_at,
            test_input,
            with_tools_input,
            without_tools_input,
            num_runs,
            model_name,
            temperature
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        BASE_TEST_INPUT,
        WITH_TOOLS_TEST_INPUT,
        WITHOUT_TOOLS_TEST_INPUT,
        NUM_RUNS,
        MODEL_NAME,
        AGENT_TEMPERATURE,
    ))
    conn.commit()
    return cur.lastrowid


def save_run_result(
    conn: sqlite3.Connection,
    session_id: int,
    label: str,
    agent_mode: str,
    run_number: int,
    user_input: str,
    output: str,
    elapsed: float,
):
    conn.execute("""
        INSERT INTO benchmark_runs (
            session_id,
            agent_label,
            agent_mode,
            run_number,
            input,
            output,
            elapsed_seconds,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        label,
        agent_mode,
        run_number,
        user_input,
        output,
        elapsed,
        datetime.now().isoformat(timespec="seconds"),
    ))
    conn.commit()


def calculate_summary(conn: sqlite3.Connection, session_id: int, agent_mode: str) -> sqlite3.Row:
    return conn.execute("""
        SELECT
            ROUND(AVG(elapsed_seconds), 2) AS average_seconds,
            ROUND(MIN(elapsed_seconds), 2) AS min_seconds,
            ROUND(MAX(elapsed_seconds), 2) AS max_seconds
        FROM benchmark_runs
        WHERE session_id = ? AND agent_mode = ?
    """, (session_id, agent_mode)).fetchone()


def get_run_times(conn: sqlite3.Connection, session_id: int, agent_mode: str) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT run_number, elapsed_seconds
        FROM benchmark_runs
        WHERE session_id = ? AND agent_mode = ?
        ORDER BY run_number
    """, (session_id, agent_mode)).fetchall()


def save_benchmark_average(
    conn: sqlite3.Connection,
    session_id: int,
    with_tools: dict,
    without_tools: dict,
) -> sqlite3.Row:
    session = conn.execute("""
        SELECT
            started_at,
            test_input,
            with_tools_input,
            without_tools_input,
            num_runs,
            model_name,
            temperature
        FROM benchmark_sessions
        WHERE id = ?
    """, (session_id,)).fetchone()

    average_diff = round(with_tools["avg"] - without_tools["avg"], 2)
    faster_agent = WITH_TOOLS_LABEL if average_diff < 0 else WITHOUT_TOOLS_LABEL
    if average_diff == 0:
        faster_agent = "equal"

    conn.execute("""
        INSERT INTO benchmark_averages (
            session_id,
            started_at,
            completed_at,
            test_input,
            with_tools_input,
            without_tools_input,
            num_runs,
            model_name,
            temperature,
            with_tools_average_seconds,
            with_tools_min_seconds,
            with_tools_max_seconds,
            without_tools_average_seconds,
            without_tools_min_seconds,
            without_tools_max_seconds,
            average_diff_seconds,
            faster_agent
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        session["started_at"],
        datetime.now().isoformat(timespec="seconds"),
        session["test_input"],
        session["with_tools_input"],
        session["without_tools_input"],
        session["num_runs"],
        session["model_name"],
        session["temperature"],
        with_tools["avg"],
        with_tools["min"],
        with_tools["max"],
        without_tools["avg"],
        without_tools["min"],
        without_tools["max"],
        average_diff,
        faster_agent,
    ))
    conn.commit()

    return conn.execute("""
        SELECT *
        FROM benchmark_averages
        WHERE session_id = ?
    """, (session_id,)).fetchone()


def get_recent_benchmark_averages(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute("""
        SELECT
            session_id,
            started_at,
            temperature,
            with_tools_average_seconds,
            with_tools_min_seconds,
            with_tools_max_seconds,
            without_tools_average_seconds,
            without_tools_min_seconds,
            without_tools_max_seconds,
            average_diff_seconds,
            faster_agent
        FROM benchmark_averages
        ORDER BY session_id DESC
        LIMIT ?
    """, (limit,)).fetchall()


def extract_agent_output(result) -> str:
    content = getattr(result, "content", None)
    if content is not None:
        return str(content)

    if isinstance(result, dict) and result.get("messages"):
        return str(result["messages"][-1].content)

    return str(result)


def run_benchmark(
    agent: Agent,
    label: str,
    agent_mode: str,
    test_input: str,
    conn: sqlite3.Connection,
    session_id: int,
):
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    print(f"Agent input: {test_input}")

    for i in range(NUM_RUNS):
        messages = [Message(role="user", content=test_input)]
        start = time.time()
        result = agent.run(messages)
        elapsed = round(time.time() - start, 2)

        output = extract_agent_output(result)
        answer = output[:80].replace("\n", " ")
        print(f"  Run {i+1}: {elapsed}s  →  {answer}...")

        save_run_result(conn, session_id, label, agent_mode, i + 1, test_input, output, elapsed)

    summary = calculate_summary(conn, session_id, agent_mode)
    run_times = get_run_times(conn, session_id, agent_mode)

    print(f"\nAverage: {summary['average_seconds']}s")
    print(f"Min: {summary['min_seconds']}s")
    print(f"Max: {summary['max_seconds']}s")
    print("Run times:")
    for run_time in run_times:
        print(f"  Run {run_time['run_number']}: {run_time['elapsed_seconds']}s")

    return {
        "label": label,
        "avg": summary["average_seconds"],
        "min": summary["min_seconds"],
        "max": summary["max_seconds"],
    }


def main():
    conn, db_path = setup_database()
    session_id = create_benchmark_session(conn)

    try:
        print("\nStarting Agno Food Agent benchmark")
        print(f"Base input: {BASE_TEST_INPUT}")
        print(f"Tool agent input: {WITH_TOOLS_TEST_INPUT}")
        print(f"No-tool agent input: {WITHOUT_TOOLS_TEST_INPUT}")
        print(f"Runs: {NUM_RUNS}")
        print(f"Temperature: {AGENT_TEMPERATURE}")
        print(f"Results database: {db_path}")
        print(f"Benchmark session ID: {session_id}")

        r1 = run_benchmark(agent_with_tools, WITH_TOOLS_LABEL, WITH_TOOLS_MODE, WITH_TOOLS_TEST_INPUT, conn, session_id)
        r2 = run_benchmark(agent_no_tools, WITHOUT_TOOLS_LABEL, WITHOUT_TOOLS_MODE, WITHOUT_TOOLS_TEST_INPUT, conn, session_id)

        average_record = save_benchmark_average(conn, session_id, r1, r2)

        print(f"\n{'='*55}")
        print("Final comparison")
        print(f"{'='*55}")
        print(f"Benchmark session ID: {average_record['session_id']}")
        print(f"Temperature: {average_record['temperature']}")
        print(
            f"  tool    → avg: {average_record['with_tools_average_seconds']}s | min: {average_record['with_tools_min_seconds']}s | max: {average_record['with_tools_max_seconds']}s"
        )
        print(
            f"  no_tool → avg: {average_record['without_tools_average_seconds']}s | min: {average_record['without_tools_min_seconds']}s | max: {average_record['without_tools_max_seconds']}s"
        )
        diff = average_record["average_diff_seconds"]
        if diff > 0:
            print(f"\nTool calling was {diff}s slower")
        elif diff < 0:
            print(f"\nTool calling was {abs(diff)}s faster")
        else:
            print("\nBoth agents had the same average")

        print("\nRecent saved averages from benchmark_averages:")
        recent_averages = get_recent_benchmark_averages(conn)
        for row in recent_averages:
            print(
                f"  Session {row['session_id']} | {row['started_at']} | "
                f"temperature: {row['temperature']} | "
                f"tool avg/min/max: {row['with_tools_average_seconds']}/{row['with_tools_min_seconds']}/{row['with_tools_max_seconds']}s | "
                f"no_tool avg/min/max: {row['without_tools_average_seconds']}/{row['without_tools_min_seconds']}/{row['without_tools_max_seconds']}s | "
                f"diff: {row['average_diff_seconds']}s | faster: {row['faster_agent']}"
            )

        print(f"\nRun inputs, outputs, and timings were saved to: {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
