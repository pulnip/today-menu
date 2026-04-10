from unittest.mock import patch, MagicMock
import requests

@patch("main.requests.post")
@patch("main.requests.get")
def test_pdf_not_found(mock_get, mock_post):
    mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("404")

    from main import run
    result = run()

    # Discord로 보낸 메시지 확인
    assert "점심 메뉴" in result

    # webhook이 실제로 호출됐는지 확인
    mock_post.assert_called_once()

    # 보낸 json 내용 검증
    sent_json = mock_post.call_args.kwargs["json"]
    assert "점심 메뉴" in sent_json["content"]

@patch("main.requests.post")
@patch("main.requests.get")
def test_unexpected_pdf_format(mock_get, mock_post):
    # HTTP 응답은 성공 (raise_for_status 통과)
    mock_get.return_value.raise_for_status = MagicMock()
    # 내용이 PDF가 아닌 쓰레기 데이터
    mock_get.return_value.content = b"%PDF-1.4 fake but valid-ish"

    from main import run
    result = run()

    assert "처리 중 오류" in result
    mock_post.assert_called_once()
