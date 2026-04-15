"""
Tier 1 tests — pure functions and form validation.

Run with:
    python manage.py test core
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from core.views import _parse_arxiv_ids, _safe_pdf_path


# ── _parse_arxiv_ids ──────────────────────────────────────────────────────


class ParseArxivIdsTests(SimpleTestCase):
    """Tests for _parse_arxiv_ids(), which extracts valid arXiv IDs
    from free-form user input."""

    # ── Basic bare IDs ────────────────────────────────────

    def test_bare_new_format(self):
        self.assertEqual(_parse_arxiv_ids("2301.12345"), ["2301.12345"])

    def test_bare_new_format_four_digits(self):
        self.assertEqual(_parse_arxiv_ids("2301.1234"), ["2301.1234"])

    def test_bare_new_format_five_digits(self):
        self.assertEqual(_parse_arxiv_ids("2301.12345"), ["2301.12345"])

    def test_bare_new_format_six_digits_invalid(self):
        self.assertEqual(_parse_arxiv_ids("2301.123456"), [])  # 6 digits — invalid

    def test_bare_legacy_format(self):
        self.assertEqual(_parse_arxiv_ids("hep-th/9901001"), ["hep-th/9901001"])

    def test_bare_legacy_with_subcategory(self):
        self.assertEqual(_parse_arxiv_ids("math.GT/0309136"), ["math.GT/0309136"])

    # ── Prefix stripping ──────────────────────────────────

    def test_abs_url(self):
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/abs/2601.19018"),
            ["2601.19018"],
        )

    def test_pdf_url(self):
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/pdf/2601.19018"),
            ["2601.19018"],
        )

    def test_arxiv_colon_prefix(self):
        self.assertEqual(_parse_arxiv_ids("arXiv:2601.19018"), ["2601.19018"])

    def test_arxiv_colon_case_insensitive(self):
        self.assertEqual(_parse_arxiv_ids("ARXIV:2301.12345"), ["2301.12345"])

    # ── Version suffix stripping ──────────────────────────

    def test_version_suffix(self):
        self.assertEqual(_parse_arxiv_ids("2601.19018v1"), ["2601.19018"])

    def test_version_suffix_high(self):
        self.assertEqual(_parse_arxiv_ids("2601.19018v12"), ["2601.19018"])

    def test_url_with_version(self):
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/abs/2601.19018v3"),
            ["2601.19018"],
        )

    # ── .pdf suffix stripping ─────────────────────────────

    def test_pdf_extension(self):
        """Versioned PDF URL — the bug that was fixed."""
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/pdf/2601.19018v2.pdf"),
            ["2601.19018"],
        )

    def test_pdf_extension_no_version(self):
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/pdf/2301.12345.pdf"),
            ["2301.12345"],
        )

    def test_pdf_extension_case_insensitive(self):
        self.assertEqual(_parse_arxiv_ids("2301.12345.PDF"), ["2301.12345"])

    # ── Query strings / fragments ─────────────────────────

    def test_query_string(self):
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/pdf/2601.19018v2.pdf?download"),
            ["2601.19018"],
        )

    def test_fragment(self):
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/abs/2601.19018#section1"),
            ["2601.19018"],
        )

    # ── Legacy IDs via URL ────────────────────────────────

    def test_legacy_id_abs_url(self):
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/abs/hep-th/9901001"),
            ["hep-th/9901001"],
        )

    def test_legacy_id_pdf_url_versioned(self):
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/pdf/hep-th/9901001v2.pdf?download"),
            ["hep-th/9901001"],
        )

    # ── Multiple IDs ──────────────────────────────────────

    def test_comma_separated(self):
        self.assertEqual(
            _parse_arxiv_ids("2301.12345, 2302.67890"),
            ["2301.12345", "2302.67890"],
        )

    def test_newline_separated(self):
        self.assertEqual(
            _parse_arxiv_ids("2301.12345\n2302.67890"),
            ["2301.12345", "2302.67890"],
        )

    def test_mixed_formats(self):
        result = _parse_arxiv_ids(
            "https://arxiv.org/abs/2601.19018, arXiv:2301.12345, 2302.67890"
        )
        self.assertEqual(result, ["2601.19018", "2301.12345", "2302.67890"])

    # ── Deduplication ─────────────────────────────────────

    def test_deduplication(self):
        self.assertEqual(
            _parse_arxiv_ids("2301.12345, 2301.12345"),
            ["2301.12345"],
        )

    def test_dedup_across_formats(self):
        """Same ID via URL and bare — should appear once."""
        self.assertEqual(
            _parse_arxiv_ids("https://arxiv.org/abs/2301.12345, 2301.12345"),
            ["2301.12345"],
        )

    # ── Invalid input ─────────────────────────────────────

    def test_empty_string(self):
        self.assertEqual(_parse_arxiv_ids(""), [])

    def test_whitespace_only(self):
        self.assertEqual(_parse_arxiv_ids("   \n  \n  "), [])

    def test_garbage(self):
        self.assertEqual(_parse_arxiv_ids("not-an-id, hello world"), [])

    def test_partial_match_ignored(self):
        """Things that look almost like IDs but aren't."""
        self.assertEqual(_parse_arxiv_ids("12345"), [])
        self.assertEqual(_parse_arxiv_ids("2301.1"), [])


# ── _safe_pdf_path ────────────────────────────────────────────────────────


class SafePdfPathTests(SimpleTestCase):
    """Tests for _safe_pdf_path(), which validates filenames against
    path traversal and non-PDF extensions."""

    def setUp(self):
        self._tmpdir = TemporaryDirectory()
        self.base = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    # ── Valid filenames ───────────────────────────────────

    def test_simple_pdf(self):
        result = _safe_pdf_path(self.base, "2301.12345.pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "2301.12345.pdf")

    def test_legacy_sanitized_pdf(self):
        """Legacy IDs are stored with _ replacing /."""
        result = _safe_pdf_path(self.base, "hep-th_9901001.pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "hep-th_9901001.pdf")

    def test_uppercase_extension(self):
        result = _safe_pdf_path(self.base, "paper.PDF")
        self.assertIsNotNone(result)

    def test_result_inside_base(self):
        result = _safe_pdf_path(self.base, "test.pdf")
        self.assertTrue(str(result).startswith(str(self.base.resolve())))

    # ── Path traversal (all stripped to safe basenames) ────

    def test_dotdot_stripped_to_basename(self):
        """../etc/passwd.pdf → basename 'passwd.pdf', resolves safely inside base."""
        result = _safe_pdf_path(self.base, "../etc/passwd.pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "passwd.pdf")
        self.assertTrue(str(result).startswith(str(self.base.resolve())))

    def test_dotdot_simple_stripped(self):
        result = _safe_pdf_path(self.base, "../passwd.pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "passwd.pdf")
        self.assertTrue(str(result).startswith(str(self.base.resolve())))

    def test_absolute_path_stripped(self):
        """Absolute paths get reduced to basename by Path().name."""
        result = _safe_pdf_path(self.base, "/etc/shadow.pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "shadow.pdf")
        self.assertTrue(str(result).startswith(str(self.base.resolve())))

    def test_directory_components_stripped(self):
        result = _safe_pdf_path(self.base, "subdir/paper.pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "paper.pdf")
        self.assertTrue(str(result).startswith(str(self.base.resolve())))

    # ── Non-PDF extensions ────────────────────────────────

    def test_txt_rejected(self):
        self.assertIsNone(_safe_pdf_path(self.base, "paper.txt"))

    def test_no_extension_rejected(self):
        self.assertIsNone(_safe_pdf_path(self.base, "paper"))

    def test_exe_rejected(self):
        self.assertIsNone(_safe_pdf_path(self.base, "malware.exe"))

    def test_double_extension_rejected(self):
        self.assertIsNone(_safe_pdf_path(self.base, "paper.pdf.exe"))

    # ── Empty / degenerate input ──────────────────────────

    def test_empty_string(self):
        self.assertIsNone(_safe_pdf_path(self.base, ""))

    def test_dot_only(self):
        self.assertIsNone(_safe_pdf_path(self.base, "."))

    def test_slash_only(self):
        self.assertIsNone(_safe_pdf_path(self.base, "/"))


# ── ProfileForm.clean_categories ──────────────────────────────────────────


class CleanCategoriesTests(SimpleTestCase):
    """Tests for ProfileForm category validation."""

    def _make_form(self, categories_str):
        """Build a ProfileForm with the given categories string and
        all other fields set to valid defaults."""
        from core.forms import ProfileForm
        return ProfileForm(data={
            "name": "Test Profile",
            "frequency": "weekly",
            "threshold": "0.6",
            "top_x": "10",
            "categories": categories_str,
        })

    # ── Valid categories ──────────────────────────────────

    def test_single_valid(self):
        form = self._make_form("cs.AI")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["categories"], ["cs.AI"])

    def test_multiple_valid(self):
        form = self._make_form("cs.AI,cs.LG,stat.ML")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["categories"],
            ["cs.AI", "cs.LG", "stat.ML"],
        )

    def test_whitespace_trimmed(self):
        form = self._make_form("  cs.AI , cs.LG  ")
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["categories"], ["cs.AI", "cs.LG"])

    def test_physics_hyphenated(self):
        """Categories like hep-th and gr-qc are valid."""
        form = self._make_form("hep-th,gr-qc,quant-ph")
        self.assertTrue(form.is_valid(), form.errors)

    def test_physics_dotted(self):
        form = self._make_form("physics.optics,cond-mat.stat-mech")
        self.assertTrue(form.is_valid(), form.errors)

    # ── Invalid categories ────────────────────────────────

    def test_empty_rejected(self):
        form = self._make_form("")
        self.assertFalse(form.is_valid())
        self.assertIn("categories", form.errors)

    def test_whitespace_only_rejected(self):
        form = self._make_form("  ,  ,  ")
        self.assertFalse(form.is_valid())
        self.assertIn("categories", form.errors)

    def test_unknown_code_rejected(self):
        form = self._make_form("cs.AI,not.real")
        self.assertFalse(form.is_valid())
        self.assertIn("categories", form.errors)
        self.assertIn("not.real", form.errors["categories"][0])

    def test_parent_group_rejected(self):
        """Parent codes like 'cs' are not leaf categories."""
        form = self._make_form("cs")
        self.assertFalse(form.is_valid())
        self.assertIn("categories", form.errors)

    def test_completely_bogus_code_rejected(self):
        form = self._make_form("fake.CATEGORY")
        self.assertFalse(form.is_valid())
        self.assertIn("categories", form.errors)

    def test_script_injection_rejected(self):
        """XSS attempt should fail validation."""
        form = self._make_form('cs.AI,</script><script>alert(1)</script>')
        self.assertFalse(form.is_valid())
        self.assertIn("categories", form.errors)


# ══════════════════════════════════════════════════════════════════════════
# Tier 2 tests — auth flows, profile CRUD, form validation (need DB)
# ══════════════════════════════════════════════════════════════════════════

from django.test import TestCase

from core.models import PBUser, Profile


class AuthFlowTests(TestCase):
    """Tests for registration, login, logout, and access control."""

    def setUp(self):
        self.user = PBUser.objects.create_user(
            email="test@example.com",
            password="SecurePass123!",
            name="Test User",
        )

    # ── Registration ──────────────────────────────────────

    def test_register_creates_user(self):
        resp = self.client.post("/auth/register/", {
            "email": "new@example.com",
            "name": "New User",
            "password": "GoodPassword99!",
            "confirm_password": "GoodPassword99!",
        })
        self.assertEqual(resp.status_code, 302)  # redirect to dashboard
        self.assertTrue(PBUser.objects.filter(email="new@example.com").exists())

    def test_register_logs_in_automatically(self):
        self.client.post("/auth/register/", {
            "email": "auto@example.com",
            "name": "",
            "password": "GoodPassword99!",
            "confirm_password": "GoodPassword99!",
        })
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)  # dashboard, not redirect to login

    def test_register_duplicate_email_rejected(self):
        resp = self.client.post("/auth/register/", {
            "email": "test@example.com",
            "name": "",
            "password": "AnotherPass99!",
            "confirm_password": "AnotherPass99!",
        })
        self.assertEqual(resp.status_code, 200)  # stays on register page
        self.assertEqual(PBUser.objects.filter(email="test@example.com").count(), 1)

    def test_register_case_insensitive_duplicate(self):
        resp = self.client.post("/auth/register/", {
            "email": "TEST@EXAMPLE.COM",
            "name": "",
            "password": "AnotherPass99!",
            "confirm_password": "AnotherPass99!",
        })
        self.assertEqual(resp.status_code, 200)  # rejected — already exists
        self.assertEqual(PBUser.objects.count(), 1)

    def test_register_password_mismatch(self):
        resp = self.client.post("/auth/register/", {
            "email": "mismatch@example.com",
            "name": "",
            "password": "GoodPassword99!",
            "confirm_password": "DifferentPassword99!",
        })
        self.assertEqual(resp.status_code, 200)  # stays on register page
        self.assertFalse(PBUser.objects.filter(email="mismatch@example.com").exists())

    def test_register_weak_password_rejected(self):
        resp = self.client.post("/auth/register/", {
            "email": "weak@example.com",
            "name": "",
            "password": "123",
            "confirm_password": "123",
        })
        self.assertEqual(resp.status_code, 200)  # stays on register page
        self.assertFalse(PBUser.objects.filter(email="weak@example.com").exists())

    # ── Login ─────────────────────────────────────────────

    def test_login_valid_credentials(self):
        resp = self.client.post("/auth/login/", {
            "email": "test@example.com",
            "password": "SecurePass123!",
        })
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

    def test_login_case_insensitive_email(self):
        resp = self.client.post("/auth/login/", {
            "email": "TEST@Example.COM",
            "password": "SecurePass123!",
        })
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

    def test_login_wrong_password(self):
        resp = self.client.post("/auth/login/", {
            "email": "test@example.com",
            "password": "WrongPassword!",
        })
        self.assertEqual(resp.status_code, 200)  # stays on login page

    def test_login_inactive_user_rejected(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post("/auth/login/", {
            "email": "test@example.com",
            "password": "SecurePass123!",
        })
        self.assertEqual(resp.status_code, 200)  # stays on login page

    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username="test@example.com", password="SecurePass123!")
        resp = self.client.get("/auth/login/")
        self.assertEqual(resp.status_code, 302)  # redirected to dashboard

    # ── Logout ────────────────────────────────────────────

    def test_logout_requires_post(self):
        self.client.login(username="test@example.com", password="SecurePass123!")
        resp = self.client.get("/auth/logout/")
        self.assertEqual(resp.status_code, 405)  # method not allowed

    def test_logout_clears_session(self):
        self.client.login(username="test@example.com", password="SecurePass123!")
        self.client.post("/auth/logout/")
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)  # redirected to login

    # ── Access control ────────────────────────────────────

    def test_unauthenticated_redirected_to_login(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login/", resp.url)

    def test_next_url_preserved(self):
        resp = self.client.get("/profiles/")
        self.assertIn("next=", resp.url)
        self.assertIn("%2Fprofiles%2F", resp.url)


class ProfileCRUDTests(TestCase):
    """Tests for profile create, edit, delete, and ownership."""

    def setUp(self):
        self.user = PBUser.objects.create_user(
            email="owner@example.com",
            password="SecurePass123!",
        )
        self.other_user = PBUser.objects.create_user(
            email="other@example.com",
            password="SecurePass123!",
        )
        self.client.login(username="owner@example.com", password="SecurePass123!")

    def _valid_profile_data(self, **overrides):
        data = {
            "name": "AI Research",
            "frequency": "weekly",
            "threshold": "0.6",
            "top_x": "25",
            "categories": "cs.AI,cs.LG",
        }
        data.update(overrides)
        return data

    # ── Create ────────────────────────────────────────────

    def test_create_profile(self):
        resp = self.client.post("/profiles/create/", self._valid_profile_data())
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Profile.objects.filter(user=self.user, name="AI Research").exists()
        )

    def test_create_profile_stores_categories(self):
        self.client.post("/profiles/create/", self._valid_profile_data())
        profile = Profile.objects.get(user=self.user, name="AI Research")
        self.assertEqual(profile.categories, ["cs.AI", "cs.LG"])

    def test_create_profile_stores_threshold(self):
        self.client.post(
            "/profiles/create/",
            self._valid_profile_data(threshold="0.45"),
        )
        profile = Profile.objects.get(user=self.user)
        self.assertAlmostEqual(profile.threshold, 0.45)

    def test_create_duplicate_name_rejected(self):
        self.client.post("/profiles/create/", self._valid_profile_data())
        resp = self.client.post("/profiles/create/", self._valid_profile_data())
        self.assertEqual(resp.status_code, 200)  # stays on form
        self.assertEqual(
            Profile.objects.filter(user=self.user, name__iexact="AI Research").count(),
            1,
        )

    def test_create_duplicate_name_case_insensitive(self):
        self.client.post("/profiles/create/", self._valid_profile_data())
        resp = self.client.post(
            "/profiles/create/",
            self._valid_profile_data(name="ai research"),
        )
        self.assertEqual(resp.status_code, 200)  # rejected
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

    def test_create_missing_categories_rejected(self):
        resp = self.client.post(
            "/profiles/create/",
            self._valid_profile_data(categories=""),
        )
        self.assertEqual(resp.status_code, 200)  # stays on form
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 0)

    # ── Edit ──────────────────────────────────────────────

    def test_edit_profile(self):
        self.client.post("/profiles/create/", self._valid_profile_data())
        profile = Profile.objects.get(user=self.user)
        resp = self.client.post(
            f"/profiles/{profile.pk}/edit/",
            self._valid_profile_data(name="Renamed"),
        )
        self.assertEqual(resp.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.name, "Renamed")

    def test_edit_preserves_other_fields(self):
        self.client.post(
            "/profiles/create/",
            self._valid_profile_data(top_x="50"),
        )
        profile = Profile.objects.get(user=self.user)
        self.client.post(
            f"/profiles/{profile.pk}/edit/",
            self._valid_profile_data(name="Updated", top_x="100"),
        )
        profile.refresh_from_db()
        self.assertEqual(profile.top_x, 100)

    # ── Delete ────────────────────────────────────────────

    def test_delete_profile(self):
        self.client.post("/profiles/create/", self._valid_profile_data())
        profile = Profile.objects.get(user=self.user)
        resp = self.client.post(f"/profiles/{profile.pk}/delete/")
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Profile.objects.filter(pk=profile.pk).exists())

    # ── Ownership ─────────────────────────────────────────

    def test_cannot_edit_other_users_profile(self):
        profile = Profile.objects.create(
            user=self.other_user, name="Other", categories=["cs.AI"],
        )
        resp = self.client.post(
            f"/profiles/{profile.pk}/edit/",
            self._valid_profile_data(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_cannot_delete_other_users_profile(self):
        profile = Profile.objects.create(
            user=self.other_user, name="Other", categories=["cs.AI"],
        )
        resp = self.client.post(f"/profiles/{profile.pk}/delete/")
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Profile.objects.filter(pk=profile.pk).exists())


class RegisterFormValidationTests(SimpleTestCase):
    """Additional form-level tests for RegisterForm."""

    def test_password_mismatch_error(self):
        from core.forms import RegisterForm
        form = RegisterForm(data={
            "email": "x@example.com",
            "name": "",
            "password": "GoodPassword99!",
            "confirm_password": "DifferentPassword99!",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Passwords do not match", str(form.errors))

    def test_weak_password_error(self):
        from core.forms import RegisterForm
        form = RegisterForm(data={
            "email": "x@example.com",
            "name": "",
            "password": "abc",
            "confirm_password": "abc",
        })
        self.assertFalse(form.is_valid())


# ══════════════════════════════════════════════════════════════════════════
# Email verification tests
# ══════════════════════════════════════════════════════════════════════════

from django.core import mail
from django.test import override_settings


class EmailVerificationOffTests(TestCase):
    """When REQUIRE_EMAIL_VERIFICATION is False (default), registration
    should auto-login and login should not check email_verified."""

    def test_register_auto_logs_in(self):
        """Default behavior: register and immediately access dashboard."""
        self.client.post("/auth/register/", {
            "email": "new@example.com",
            "name": "",
            "password": "GoodPassword99!",
            "confirm_password": "GoodPassword99!",
        })
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)  # dashboard, not redirect

    def test_register_does_not_send_email(self):
        self.client.post("/auth/register/", {
            "email": "no-email@example.com",
            "name": "",
            "password": "GoodPassword99!",
            "confirm_password": "GoodPassword99!",
        })
        self.assertEqual(len(mail.outbox), 0)

    def test_login_allows_unverified_user(self):
        user = PBUser.objects.create_user(
            email="unverified@example.com", password="SecurePass123!",
        )
        self.assertFalse(user.email_verified)
        resp = self.client.post("/auth/login/", {
            "email": "unverified@example.com",
            "password": "SecurePass123!",
        })
        self.assertRedirects(resp, "/", fetch_redirect_response=False)


@override_settings(REQUIRE_EMAIL_VERIFICATION=True)
class EmailVerificationOnTests(TestCase):
    """When REQUIRE_EMAIL_VERIFICATION is True, registration should
    send a verification email and block login until verified."""

    # ── Registration ──────────────────────────────────────

    def test_register_sends_verification_email(self):
        resp = self.client.post("/auth/register/", {
            "email": "verify@example.com",
            "name": "Test",
            "password": "GoodPassword99!",
            "confirm_password": "GoodPassword99!",
        })
        self.assertEqual(resp.status_code, 200)  # renders verify_email_sent
        self.assertContains(resp, "Check Your Email")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verify@example.com", mail.outbox[0].to)
        self.assertIn("verify-email", mail.outbox[0].body)

    def test_register_does_not_auto_login(self):
        self.client.post("/auth/register/", {
            "email": "nologin@example.com",
            "name": "",
            "password": "GoodPassword99!",
            "confirm_password": "GoodPassword99!",
        })
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)  # redirected to login

    def test_register_creates_unverified_user(self):
        self.client.post("/auth/register/", {
            "email": "unverified@example.com",
            "name": "",
            "password": "GoodPassword99!",
            "confirm_password": "GoodPassword99!",
        })
        user = PBUser.objects.get(email="unverified@example.com")
        self.assertFalse(user.email_verified)

    # ── Login blocked ─────────────────────────────────────

    def test_login_blocked_for_unverified_user(self):
        PBUser.objects.create_user(
            email="blocked@example.com", password="SecurePass123!",
        )
        resp = self.client.post("/auth/login/", {
            "email": "blocked@example.com",
            "password": "SecurePass123!",
        })
        self.assertEqual(resp.status_code, 200)  # stays on login
        self.assertContains(resp, "verify your email")
        self.assertContains(resp, "resend-verification")

    def test_login_works_for_verified_user(self):
        user = PBUser.objects.create_user(
            email="verified@example.com", password="SecurePass123!",
        )
        user.email_verified = True
        user.save()
        resp = self.client.post("/auth/login/", {
            "email": "verified@example.com",
            "password": "SecurePass123!",
        })
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

    # ── Verification link ─────────────────────────────────

    def test_verify_email_link_works(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = PBUser.objects.create_user(
            email="link@example.com", password="SecurePass123!",
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        resp = self.client.get(f"/auth/verify-email/{uid}/{token}/")
        self.assertRedirects(resp, "/auth/login/", fetch_redirect_response=False)

        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    def test_verify_email_invalid_token_rejected(self):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = PBUser.objects.create_user(
            email="bad@example.com", password="SecurePass123!",
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        resp = self.client.get(f"/auth/verify-email/{uid}/bad-token/")
        self.assertRedirects(resp, "/auth/login/", fetch_redirect_response=False)

        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    # ── Resend ────────────────────────────────────────────

    def test_resend_verification(self):
        PBUser.objects.create_user(
            email="resend@example.com", password="SecurePass123!",
        )
        # Trigger login to set session key
        self.client.post("/auth/login/", {
            "email": "resend@example.com",
            "password": "SecurePass123!",
        })
        resp = self.client.get("/auth/resend-verification/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Check Your Email")
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_without_session_redirects(self):
        resp = self.client.get("/auth/resend-verification/")
        self.assertRedirects(resp, "/auth/login/", fetch_redirect_response=False)

