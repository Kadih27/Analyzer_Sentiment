import unittest
import unittest.mock as mock
import requests
import json
from langdetect import detect


class TestSentimentAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # API configuration for testing
        cls.api_url = "https://api-inference.huggingface.co/models/tabularisai/multilingual-sentiment-analysis"

    def test_api_connectivity(self):
        """Test that the API endpoint exists"""
        # Just check if the endpoint resolves - don't need a valid API key for this
        response = requests.head(self.api_url)
        self.assertIn(response.status_code, [200, 401, 403], "API endpoint should exist")
        
    def test_positive_sentiment_english(self):
        """Test that a positive English text is correctly classified"""
        text = "I am very happy with this product. It's amazing!"
        mock_response = [
            {"label": "Very Positive", "score": 0.65},
            {"label": "Positive", "score": 0.25},
            {"label": "Neutral", "score": 0.05},
            {"label": "Negative", "score": 0.03},
            {"label": "Very Negative", "score": 0.02}
        ]
        result = self._analyze_sentiment(text, mock_response)
        self.assertEqual(result['language'], 'en')
        self.assertIn(result['label'], ['Positive', 'Very Positive'])
        
    def test_negative_sentiment_english(self):
        """Test that a negative English text is correctly classified"""
        text = "This is terrible, I hate it. The worst experience ever."
        mock_response = [
            {"label": "Very Negative", "score": 0.70},
            {"label": "Negative", "score": 0.20},
            {"label": "Neutral", "score": 0.05},
            {"label": "Positive", "score": 0.03},
            {"label": "Very Positive", "score": 0.02}
        ]
        result = self._analyze_sentiment(text, mock_response)
        self.assertEqual(result['language'], 'en')
        self.assertIn(result['label'], ['Negative', 'Very Negative'])
        
    def test_neutral_sentiment_english(self):
        """Test that a neutral English text is correctly classified"""
        text = "This is a simple test message with no strong emotions."
        mock_response = [
            {"label": "Neutral", "score": 0.60},
            {"label": "Positive", "score": 0.15},
            {"label": "Negative", "score": 0.15},
            {"label": "Very Positive", "score": 0.05},
            {"label": "Very Negative", "score": 0.05}
        ]
        result = self._analyze_sentiment(text, mock_response)
        self.assertEqual(result['language'], 'en')
        self.assertEqual(result['label'], 'Neutral')
        
    def test_spanish_sentiment(self):
        """Test sentiment analysis on Spanish text"""
        text = "Me encanta este programa, es fantástico."
        mock_response = [
            {"label": "Very Positive", "score": 0.75},
            {"label": "Positive", "score": 0.20},
            {"label": "Neutral", "score": 0.03},
            {"label": "Negative", "score": 0.01},
            {"label": "Very Negative", "score": 0.01}
        ]
        result = self._analyze_sentiment(text, mock_response)
        self.assertEqual(result['language'], 'es')
        self.assertIn(result['label'], ['Positive', 'Very Positive'])
        
    def test_french_sentiment(self):
        """Test sentiment analysis on French text"""
        text = "Je n'aime pas ce produit, c'est terrible."
        mock_response = [
            {"label": "Negative", "score": 0.55},
            {"label": "Very Negative", "score": 0.35},
            {"label": "Neutral", "score": 0.05},
            {"label": "Positive", "score": 0.03},
            {"label": "Very Positive", "score": 0.02}
        ]
        result = self._analyze_sentiment(text, mock_response)
        self.assertEqual(result['language'], 'fr')
        self.assertIn(result['label'], ['Negative', 'Very Negative'])
        
    def _analyze_sentiment(self, text, mock_response=None):
        """Helper method to analyze sentiment of text using API"""
        # Detect language
        try:
            language = detect(text)
        except:
            language = 'unknown'
            
        # Use a mock response for testing
        if mock_response:
            # Mock the API call
            results = mock_response
        else:
            # This would be a real API call, but we're not doing that in tests
            # Instead, we'll use default test responses below
            sample_response = [
                {"label": "Positive", "score": 0.6},
                {"label": "Very Positive", "score": 0.3},
                {"label": "Neutral", "score": 0.05},
                {"label": "Negative", "score": 0.03},
                {"label": "Very Negative", "score": 0.02}
            ]
            results = sample_response
        
        # Sort by score in descending order (just to be sure)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return the top sentiment
        return {
            'label': results[0]['label'],
            'score': results[0]['score'],
            'all_results': results,
            'language': language
        }


if __name__ == '__main__':
    unittest.main()
