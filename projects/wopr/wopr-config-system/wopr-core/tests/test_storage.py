import pytest
from unittest.mock import Mock, patch
from wopr.storage import imagefilename, StorageError


def test_imagefilename_basic():
    """Test basic image filename generation"""
    with patch('wopr.storage.get_str') as mock_get_str, \
         patch('wopr.storage.get_list') as mock_get_list, \
         patch('wopr.storage.get_bool') as mock_get_bool:
        
        # Mock config responses
        mock_get_list.side_effect = lambda key: {
            'image_subjects': ['capture', 'move', 'setup'],
            'storage.image_extensions': ['jpg', 'png']
        }[key]
        
        mock_get_str.side_effect = lambda key: {
            'storage.default_extension': 'jpg',
            'filenames.timestamp_format': '%Y%m%d-%H%M%S',
            'filenames.image_template': '{timestamp}-{subject}.{extension}',
            'storage.base_path': '/tmp/test',
            'storage.games_subdir': 'games'
        }[key]
        
        mock_get_bool.return_value = True
        
        # Test
        filepath = imagefilename('test123', 'capture')
        
        assert 'test123' in filepath
        assert 'capture' in filepath
        assert filepath.endswith('.jpg')


def test_imagefilename_with_sequence():
    """Test filename generation with sequence number"""
    with patch('wopr.storage.get_str') as mock_get_str, \
         patch('wopr.storage.get_list') as mock_get_list, \
         patch('wopr.storage.get_bool') as mock_get_bool:
        
        mock_get_list.side_effect = lambda key: {
            'image_subjects': ['capture', 'move', 'setup'],
            'storage.image_extensions': ['jpg', 'png']
        }[key]
        
        mock_get_str.side_effect = lambda key: {
            'storage.default_extension': 'jpg',
            'filenames.timestamp_format': '%Y%m%d-%H%M%S',
            'filenames.image_with_sequence_template': '{timestamp}-{subject}-{sequence:03d}.{extension}',
            'storage.base_path': '/tmp/test',
            'storage.games_subdir': 'games'
        }[key]
        
        mock_get_bool.return_value = True
        
        filepath = imagefilename('test123', 'move', sequence=5)
        
        assert 'move-005' in filepath


def test_imagefilename_invalid_subject():
    """Test that invalid subject raises ValueError"""
    with patch('wopr.storage.get_list') as mock_get_list:
        mock_get_list.return_value = ['capture', 'move', 'setup']
        
        with pytest.raises(ValueError, match="Invalid subject"):
            imagefilename('test123', 'invalid_subject')


def test_imagefilename_invalid_sequence_type():
    """Test that non-integer sequence raises TypeError"""
    with pytest.raises(TypeError, match="sequence must be an integer"):
        imagefilename('test123', 'capture', sequence="not_an_int")
