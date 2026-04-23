import pytest
from pathlib import Path
from ragapp.services.parsers.textract_parser import AWSTextractParser
from ragapp.schemas.parsing import DocumentType

@pytest.mark.asyncio
@pytest.mark.skipif(
    not all([
        os.getenv("AWS_ACCESS_KEY_ID"),
        os.getenv("AWS_SECRET_ACCESS_KEY"),
        os.getenv("AWS_DEFAULT_REGION"),
    ]),
    reason="AWS credentials not fully configured"
)
async def test_textract_parse_manual_file():
    file_path = Path("test_data/Invoice.pdf")
    assert file_path.exists(), f"File not found: {file_path}"
    parser = AWSTextractParser()
    result = await parser.parse(file_path, DocumentType.PDF)
    print(f"\n--- Textract Output for {file_path.name} ---")
    print(f"Pages: {result.total_pages}")
    print(f"Text length: {len(result.full_text)} chars")
    print(f"Tables: {result.total_tables}")
    print(f"Forms: {result.total_forms}")
    print(f"Text preview: {result.full_text[:500]}...")
    assert result.total_pages > 0
    assert len(result.full_text) > 0
