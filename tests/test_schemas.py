"""Unit tests for schema enums"""
import pytest


class TestEnums:
    def test_frequency_enum_values(self):
        """Test that frequency enum has expected values"""
        from schemas import FrequencyEnum
        
        assert FrequencyEnum.daily.value == "daily"
        assert FrequencyEnum.weekly.value == "weekly"
        assert FrequencyEnum.monthly.value == "monthly"
    
    def test_threshold_enum_values(self):
        """Test that threshold enum has expected values"""
        from schemas import ThresholdEnum
        
        assert ThresholdEnum.low.value == "low"
        assert ThresholdEnum.medium.value == "medium"
        assert ThresholdEnum.high.value == "high"
    
    def test_source_enum_values(self):
        """Test that source enum has expected values"""
        from schemas import SourceEnum
        
        assert SourceEnum.user.value == "user"
        assert SourceEnum.arxiv.value == "arxiv"
    
    def test_mode_enum_values(self):
        """Test that mode enum has expected values"""
        from schemas import ModeEnum
        
        assert ModeEnum.abstract.value == "abstract"
        assert ModeEnum.full.value == "full"
    
    def test_type_enum_values(self):
        """Test that type enum has expected values"""
        from schemas import TypeEnum
        
        assert TypeEnum.abstract.value == "abstract"
        assert TypeEnum.section.value == "section"
    
    def test_status_enum_values(self):
        """Test that status enum has expected values"""
        from schemas import StatusEnum
        
        assert StatusEnum.sent.value == "sent"
        assert StatusEnum.failed.value == "failed"


class TestEnumMembership:
    @pytest.mark.parametrize("enum_class,expected_members", [
        ("FrequencyEnum", ["daily", "weekly", "monthly"]),
        ("ThresholdEnum", ["low", "medium", "high"]),
        ("SourceEnum", ["user", "arxiv"]),
        ("ModeEnum", ["abstract", "full"]),
        ("TypeEnum", ["abstract", "section"]),
    ])
    def test_enum_has_all_members(self, enum_class, expected_members):
        """Test that enums have all expected members"""
        import schemas
        enum = getattr(schemas, enum_class)
        
        for member in expected_members:
            assert hasattr(enum, member)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])