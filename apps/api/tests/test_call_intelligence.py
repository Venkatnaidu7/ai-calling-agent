from app.services.call_intelligence import build_transcript_text


def test_build_transcript_text_preserves_speaker_order():
    class Segment:
        def __init__(self, speaker, text):
            self.speaker = speaker
            self.text = text
    result = build_transcript_text([Segment('CUSTOMER', 'Hello'), Segment('ASSISTANT', 'Hi, how can I help?')])
    assert result == 'CUSTOMER: Hello\nASSISTANT: Hi, how can I help?'


def test_build_transcript_text_skips_empty_segments():
    class Segment:
        def __init__(self, speaker, text):
            self.speaker = speaker
            self.text = text
    result = build_transcript_text([Segment('CUSTOMER', ''), Segment('CUSTOMER', 'Need help')])
    assert result == 'CUSTOMER: Need help'
