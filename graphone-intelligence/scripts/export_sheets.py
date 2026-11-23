import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete

from src.config.settings import get_settings
from src.exporters.google_sheets import GoogleSheetsExporter, GoogleSheetsService
from src.storage.database import init_db, session_factory
from src.storage.models import ExportCheckpoint


async def main() -> None:
    reset_checkpoints = "--reset" in sys.argv
    settings = get_settings()
    sheet_id = settings.google_sheets_spreadsheet_id
    creds_file = settings.google_application_credentials

    if not sheet_id or not creds_file:
        print("Error: Missing Google Sheets configuration in .env:")
        print("  - GOOGLE_SHEETS_SPREADSHEET_ID")
        print("  - GOOGLE_APPLICATION_CREDENTIALS")
        print("Tip: You can use 'scripts/export_csv.py' to generate CSVs for manual upload.")
        sys.exit(1)

    await init_db()
    if reset_checkpoints:
        print("Resetting export checkpoints for full sync...")
        async with session_factory() as session:
            await session.execute(delete(ExportCheckpoint))
            await session.commit()

    service = GoogleSheetsService(
        spreadsheet_id=sheet_id,
        credentials_file=creds_file,
    )
    exporter = GoogleSheetsExporter(sheets=service)

    print(f"Exporting data to Google Spreadsheet ID: {sheet_id}...")
    async with session_factory() as session:
        results = await exporter.export_all(session)

    print("\nGoogle Sheets synchronization results:")
    for tab, count in results.items():
        print(f"  - {tab}: {count} rows synced")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
