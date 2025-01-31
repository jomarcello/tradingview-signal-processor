# Optimalisaties:
# 1. Gebruik geavanceerde NLP-technieken
# 2. Sentiment analyse integratie
# 3. Samenvattingskwaliteit meten

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

def enhance_summarization(text):
    # Multi-document summarization
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    
    # Combineer verschillende technieken
    lsa_summarizer = LsaSummarizer()
    lsa_summary = lsa_summarizer(parser.document, sentences_count=3)
    
    # Sentiment analyse
    sentiment = analyze_sentiment(text)
    
    return {
        'summary': " ".join(str(s) for s in lsa_summary),
        'sentiment_score': sentiment['score'],
        'key_terms': extract_key_phrases(text)
    } 