import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup PostgreSQL EMS via Docker Compose.")
    parser.add_argument("--database", default="ems")
    parser.add_argument("--postgres-user", default="ems")
    parser.add_argument("--output-directory", default="backups")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.database):
        parser.error("nama database hanya boleh berisi huruf, angka, underscore, dan tanda hubung")
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.postgres_user):
        parser.error("nama user PostgreSQL hanya boleh berisi huruf, angka, dan underscore")

    repository_root = Path(__file__).resolve().parent.parent
    output_directory = Path(args.output_directory)
    if not output_directory.is_absolute():
        output_directory = repository_root / output_directory
    output_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dump_path = output_directory / f"ems-{timestamp}.dump"
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "db",
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "-U",
        args.postgres_user,
        "-d",
        args.database,
    ]

    try:
        with dump_path.open("wb") as dump_file:
            result = subprocess.run(
                command,
                cwd=repository_root,
                stdout=dump_file,
                stderr=subprocess.PIPE,
                check=False,
                text=True,
            )
        if result.returncode != 0:
            raise RuntimeError(
                f"pg_dump gagal (exit {result.returncode}): {result.stderr.strip()}"
            )
        if dump_path.stat().st_size == 0:
            raise RuntimeError("pg_dump menghasilkan file kosong.")
    except (OSError, RuntimeError) as error:
        dump_path.unlink(missing_ok=True)
        print(f"Backup gagal: {error}", file=sys.stderr)
        return 1

    print(f"Backup database tersimpan: {dump_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
