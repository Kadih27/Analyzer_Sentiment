import json
import unittest
import unittest.mock as mock
import requests
from app import app


class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_home_page(self):
        """Test that the home page loads correctly"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Multilingual Sentiment Analysis', response.data)
    
    def test_analyze_empty_text(self):
        """Test that trying to analyze empty text returns an error"""
        response = self.app.post('/analyze',
                               data=json.dumps({'text': ''}),
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('Empty text', data['message'])
    
    def test_analyze_missing_text(self):
        """Test that making a request without text returns an error"""
        response = self.app.post('/analyze',
                               data=json.dumps({}),
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('No text', data['message'])
    
    @mock.patch('requests.post')
    def test_analyze_valid_text(self, mock_post):
        """Test that analyzing valid text returns expected format with mocked API response"""
        # Mock the Hugging Face API response
        mock_api_response = mock.Mock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = [
            [{"label": "Positive", "score": 0.6},
             {"label": "Very Positive", "score": 0.3},
             {"label": "Neutral", "score": 0.05},
             {"label": "Negative", "score": 0.03},
             {"label": "Very Negative", "score": 0.02}]
        ]
        mock_post.return_value = mock_api_response
        
        # Test the API endpoint
        test_text = "This is a test message."
        response = self.app.post('/analyze',
                               data=json.dumps({'text': test_text}),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('label', data)
        self.assertIn('score', data)
        self.assertIn('language', data)
        self.assertIn('all_results', data)
        self.assertIsInstance(data['all_results'], list)
        self.assertGreater(len(data['all_results']), 0)
        self.assertEqual(data['language'], 'en')  # Assuming the test text is in English


if __name__ == '__main__':
    unittest.main()
