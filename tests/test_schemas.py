"""Unit tests for schema enums and threshold validation"""
import pytest


class TestEnums:
    def test_frequency_enum_values(self):
        """Test that frequency enum has expected values"""
        from schemas import FrequencyEnum
        
        assert FrequencyEnum.daily.value == "daily"
        assert FrequencyEnum.weekly.value == "weekly"
        assert FrequencyEnum.monthly.value == "monthly"
    
    def test_threshold_is_float(self):
        """Test that threshold is now a float field not an enum"""
        from schemas import ProfileCreate
        import inspect
        
        fields = ProfileCreate.model_fields
        assert 'threshold' in fields
        assert fields['threshold'].default == 0.6
    
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


class TestThreshold:
    def test_threshold_default_value(self):
        """Test that threshold defaults to 0.6"""
        from schemas import ProfileCreate
        profile = ProfileCreate(
            user_id=1,
            name="test",
            keywords=["ml"],
            categories=["cs.LG"],
            frequency="weekly"
        )
        assert profile.threshold == 0.6

    def test_threshold_accepts_float(self):
        """Test that threshold accepts a float value"""
        from schemas import ProfileCreate
        profile = ProfileCreate(
            user_id=1,
            name="test",
            keywords=["ml"],
            categories=["cs.LG"],
            frequency="weekly",
            threshold=0.55
        )
        assert profile.threshold == 0.55

    def test_threshold_range(self):
        """Test threshold values across expected range"""
        from schemas import ProfileCreate
        for val in [0.4, 0.5, 0.6, 0.75]:
            profile = ProfileCreate(
                user_id=1,
                name="test",
                keywords=["ml"],
                categories=["cs.LG"],
                frequency="weekly",
                threshold=val
            )
            assert profile.threshold == val


class TestEnumMembership:
    @pytest.mark.parametrize("enum_class,expected_members", [
        ("FrequencyEnum", ["daily", "weekly", "monthly"]),
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