"""Comprehensive tests for AI router error mapping and classification functionality."""

from typing import Pattern

from backend.api.routers.ai import ERROR_KEYWORD_MAPPING, classify_error_status_code


class TestErrorKeywordMapping:
    """Test the ERROR_KEYWORD_MAPPING module constant."""

    def test_error_keyword_mapping_structure(self):
        """Test that ERROR_KEYWORD_MAPPING has the expected structure."""
        # Verify it's a dictionary
        assert isinstance(ERROR_KEYWORD_MAPPING, dict)

        # Verify all keys are integers (HTTP status codes)
        for status_code in ERROR_KEYWORD_MAPPING.keys():
            assert isinstance(status_code, int)
            assert 400 <= status_code <= 599  # Valid HTTP error status codes

        # Verify all values are non-empty lists of strings or Pattern objects
        for keywords in ERROR_KEYWORD_MAPPING.values():
            assert isinstance(keywords, list)
            assert len(keywords) > 0
            for keyword in keywords:
                # Keywords can be either strings or compiled regex Pattern objects
                assert isinstance(keyword, (str, Pattern))
                if isinstance(keyword, str):
                    assert len(keyword.strip()) > 0

    def test_error_keyword_mapping_completeness(self):
        """Test that ERROR_KEYWORD_MAPPING covers all expected error categories."""
        expected_status_codes = {401, 403, 429, 400, 503, 504}
        actual_status_codes = set(ERROR_KEYWORD_MAPPING.keys())

        # Use superset check to be future-proof when adding new classes
        assert expected_status_codes.issubset(actual_status_codes), (
            f"Missing expected status codes: {expected_status_codes - actual_status_codes}"
        )

    def test_error_keyword_mapping_401_auth_keywords(self):
        """Test that 401 status code includes authentication-related keywords."""
        auth_keywords = ERROR_KEYWORD_MAPPING[401]

        # Check for critical authentication keywords (strings only)
        expected_string_keywords = {
            "invalid api key",
            "authentication failed",
            "unauthorized",
            "api key",
            "invalid credentials",
        }

        # Extract string keywords from the list (excluding Pattern objects)
        actual_string_keywords = {kw for kw in auth_keywords if isinstance(kw, str)}
        assert expected_string_keywords.issubset(actual_string_keywords)

        # Check that regex patterns are present (Pattern objects)
        regex_patterns = [kw for kw in auth_keywords if isinstance(kw, Pattern)]
        assert len(regex_patterns) > 0, "Should have at least one regex pattern for auth keywords"

        # Verify specific auth regex pattern exists
        auth_pattern_found = any(
            isinstance(kw, Pattern) and kw.pattern == r"\bauth(?:entication|orization)?\b" for kw in auth_keywords
        )
        assert auth_pattern_found, "Should have auth word boundary regex pattern"

    def test_error_keyword_mapping_403_permission_keywords(self):
        """Test that 403 status code includes permission-related keywords."""
        permission_keywords = ERROR_KEYWORD_MAPPING[403]

        expected_keywords = {"permission denied", "access denied", "forbidden", "not allowed"}

        actual_keywords = set(permission_keywords)
        assert expected_keywords.issubset(actual_keywords)

    def test_error_keyword_mapping_429_rate_limit_keywords(self):
        """Test that 429 status code includes rate limiting keywords."""
        rate_limit_keywords = ERROR_KEYWORD_MAPPING[429]

        # Check for critical rate limiting keywords (strings only)
        expected_string_keywords = {"quota exceeded", "rate limit", "too many requests"}

        # Extract string keywords from the list (excluding Pattern objects)
        actual_string_keywords = {kw for kw in rate_limit_keywords if isinstance(kw, str)}
        assert expected_string_keywords.issubset(actual_string_keywords)

        # Check that regex patterns are present (Pattern objects)
        regex_patterns = [kw for kw in rate_limit_keywords if isinstance(kw, Pattern)]
        assert len(regex_patterns) > 0, "Should have at least one regex pattern for rate limit keywords"

        # Verify specific regex patterns exist
        quota_pattern_found = any(isinstance(kw, Pattern) and kw.pattern == r"\bquota\b" for kw in rate_limit_keywords)
        rate_pattern_found = any(isinstance(kw, Pattern) and r"\brate(?:" in kw.pattern for kw in rate_limit_keywords)
        assert quota_pattern_found, "Should have quota word boundary regex pattern"
        assert rate_pattern_found, "Should have tightened rate limit regex pattern to avoid false positives"

    def test_error_keyword_mapping_400_bad_request_keywords(self):
        """Test that 400 status code includes bad request keywords."""
        bad_request_keywords = ERROR_KEYWORD_MAPPING[400]

        expected_keywords = {"invalid input", "bad request", "malformed", "validation error"}

        actual_keywords = set(bad_request_keywords)
        assert expected_keywords.issubset(actual_keywords)

    def test_error_keyword_mapping_503_service_unavailable_keywords(self):
        """Test that 503 status code includes service unavailable keywords."""
        service_keywords = ERROR_KEYWORD_MAPPING[503]

        expected_keywords = {"service unavailable", "temporarily unavailable", "maintenance", "overloaded"}

        actual_keywords = set(service_keywords)
        assert expected_keywords.issubset(actual_keywords)

    def test_error_keyword_mapping_504_timeout_keywords(self):
        """Test that 504 status code includes timeout keywords."""
        timeout_keywords = ERROR_KEYWORD_MAPPING[504]

        expected_keywords = {"timeout", "timed out", "deadline exceeded"}

        actual_keywords = set(timeout_keywords)
        assert expected_keywords.issubset(actual_keywords)

    def test_no_duplicate_keywords_across_categories(self):
        """Test that keywords are not duplicated across different status codes."""
        all_keywords = []

        for keywords in ERROR_KEYWORD_MAPPING.values():
            # Convert Pattern objects to their string representation for comparison
            processed_keywords = []
            for kw in keywords:
                if isinstance(kw, Pattern):
                    processed_keywords.append(kw.pattern)  # Use pattern string for comparison
                else:
                    processed_keywords.append(kw)
            all_keywords.extend(processed_keywords)

        # Check for duplicates
        unique_keywords = set(all_keywords)
        assert len(all_keywords) == len(unique_keywords), "Found duplicate keywords across categories"

    def test_keywords_are_lowercase(self):
        """Test that all string keywords are in lowercase for consistent matching."""
        for keywords in ERROR_KEYWORD_MAPPING.values():
            for keyword in keywords:
                # Only check string keywords, skip Pattern objects
                if isinstance(keyword, str):
                    assert keyword == keyword.lower(), f"Keyword '{keyword}' should be lowercase"
                # Pattern objects are compiled, so we don't need to check case

    def test_keywords_are_stripped(self):
        """Test that all string keywords are properly stripped of whitespace."""
        for keywords in ERROR_KEYWORD_MAPPING.values():
            for keyword in keywords:
                # Only check string keywords, skip Pattern objects
                if isinstance(keyword, str):
                    assert keyword == keyword.strip(), f"Keyword '{keyword}' should be stripped"
                # Pattern objects don't have leading/trailing whitespace in their patterns


class TestClassifyErrorStatusCode:
    """Test the classify_error_status_code helper function."""

    def test_classify_error_status_code_empty_input(self):
        """Test classification with empty or None input."""
        assert classify_error_status_code("") is None
        assert classify_error_status_code(None) is None
        assert classify_error_status_code("   ") is None

    def test_classify_error_status_code_401_auth_errors(self):
        """Test classification of authentication errors (401)."""
        auth_messages = [
            "Invalid API key provided",
            "Authentication failed for user",
            "Unauthorized access attempt",
            "API key is malformed",
            "Auth token expired",
            "Invalid credentials supplied",
            "Invalid token supplied",
            "Token expired yesterday",
        ]

        for message in auth_messages:
            result = classify_error_status_code(message)
            assert result == 401, f"Message '{message}' should classify as 401"

    def test_classify_error_status_code_403_permission_errors(self):
        """Test classification of permission errors (403)."""
        permission_messages = [
            "Permission denied to access resource",
            "Access denied due to insufficient privileges",
            "Forbidden operation requested",
            "You are not allowed to perform this action",
            "Insufficient permissions for this operation",
        ]

        for message in permission_messages:
            result = classify_error_status_code(message)
            assert result == 403, f"Message '{message}' should classify as 403"

    def test_classify_error_status_code_429_rate_limit_errors(self):
        """Test classification of rate limiting errors (429)."""
        rate_limit_messages = [
            "Quota exceeded for this request",  # Avoid "api key" keyword conflict
            "Rate limit reached, please try again later",
            "Too many requests in short time",
            "Daily quota has been exceeded",
            "Request rate too high",
            "API throttle limit reached",
            "Quota limit exceeded for today",
        ]

        for message in rate_limit_messages:
            result = classify_error_status_code(message)
            assert result == 429, f"Message '{message}' should classify as 429"

    def test_classify_error_status_code_400_bad_request_errors(self):
        """Test classification of bad request errors (400)."""
        bad_request_messages = [
            "Invalid input parameters provided",
            "Bad request format detected",
            "Malformed JSON in request body",
            "Invalid request structure",
            "Validation error in input data",
            "Invalid parameter 'temperature' value",
        ]

        for message in bad_request_messages:
            result = classify_error_status_code(message)
            assert result == 400, f"Message '{message}' should classify as 400"

    def test_classify_error_status_code_503_service_unavailable_errors(self):
        """Test classification of service unavailable errors (503)."""
        service_messages = [
            "Service unavailable at this time",
            "API temporarily unavailable for maintenance",
            "Server under maintenance",
            "Service overloaded, try again later",
            "Server busy processing requests",
        ]

        for message in service_messages:
            result = classify_error_status_code(message)
            assert result == 503, f"Message '{message}' should classify as 503"

    def test_classify_error_status_code_504_timeout_errors(self):
        """Test classification of timeout errors (504)."""
        timeout_messages = [
            "Request timeout occurred",
            "Operation timed out after 30 seconds",
            "Deadline exceeded for this request",
        ]

        for message in timeout_messages:
            result = classify_error_status_code(message)
            assert result == 504, f"Message '{message}' should classify as 504"

    def test_classify_error_status_code_case_insensitive(self):
        """Test that classification is case-insensitive."""
        test_cases = [
            ("INVALID API KEY", 401),
            ("Permission Denied", 403),
            ("QUOTA EXCEEDED", 429),
            ("Bad Request", 400),
            ("SERVICE UNAVAILABLE", 503),
            ("TIMEOUT ERROR", 504),
        ]

        for message, expected_status in test_cases:
            result = classify_error_status_code(message)
            assert result == expected_status, f"Message '{message}' should classify as {expected_status}"

    def test_classify_error_status_code_whitespace_handling(self):
        """Test that classification handles whitespace correctly."""
        test_cases = [
            ("  invalid api key  ", 401),
            ("\tpermission denied\n", 403),
            ("   quota exceeded   ", 429),
        ]

        for message, expected_status in test_cases:
            result = classify_error_status_code(message)
            assert result == expected_status, f"Message '{message}' should classify as {expected_status}"

    def test_classify_error_status_code_priority_order(self):
        """Test that more specific errors are classified first (precedence)."""
        # Test that "invalid api key" (401) takes precedence over "invalid" (400)
        result = classify_error_status_code("invalid api key provided")
        assert result == 401, "Should classify as 401 (auth) not 400 (bad request) due to precedence"

        # Test that "quota exceeded" (429) takes precedence over "quota" (429)
        # Both should map to 429, but testing the specificity
        result = classify_error_status_code("quota exceeded error")
        assert result == 429

    def test_classify_error_status_code_substring_matching(self):
        """Test that classification works with substring matching."""
        test_cases = [
            ("The API key provided is invalid", 401),
            ("User permission denied for this resource", 403),
            ("Daily quota has been exceeded", 429),
            ("Request contains malformed data", 400),
            ("Backend service unavailable", 503),
            ("Request timeout after 30s", 504),
        ]

        for message, expected_status in test_cases:
            result = classify_error_status_code(message)
            assert result == expected_status, f"Message '{message}' should classify as {expected_status}"

    def test_classify_error_status_code_unknown_errors(self):
        """Test that unknown error messages return None."""
        unknown_messages = [
            "Something went wrong",
            "Error code 12345",
            "Unexpected system failure",
            "Database connection lost",
            "Memory allocation failed",
            "",
            "   ",
        ]

        for message in unknown_messages:
            result = classify_error_status_code(message)
            assert result is None, f"Unknown message '{message}' should return None"

    def test_classify_error_status_code_complex_messages(self):
        """Test classification with complex, real-world error messages."""
        complex_messages = [
            # Real Gemini API error examples
            ("Error 401: The request is missing a valid API key.", 401),
            ("Error 403: Permission denied. The caller does not have access to this resource.", 403),
            ("Error 429: Quota exceeded. The caller has exceeded the rate limit.", 429),
            ("Error 400: Invalid request. The request is malformed or missing required parameters.", 400),
            ("Error 503: The service is temporarily unavailable. Please try again later.", 503),
            ("Error 504: Gateway timeout. The request timed out.", 504),
            # Multi-word complex scenarios
            ("Authentication failed: invalid API key format detected in request headers", 401),
            ("Permission denied: user does not have sufficient access rights to perform this operation", 403),
            ("Rate limiting active: quota limit exceeded for this request today", 429),
            ("Validation error: malformed JSON in request body causes parsing failure", 400),
            ("Service temporarily unavailable due to scheduled maintenance window", 503),
            ("Request deadline exceeded: operation timed out after maximum allowed duration", 504),
        ]

        for message, expected_status in complex_messages:
            result = classify_error_status_code(message)
            assert result == expected_status, f"Complex message '{message}' should classify as {expected_status}"

    def test_classify_error_status_code_edge_cases(self):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            # Multiple matching keywords - should return first match based on dict iteration order
            ("invalid api key and quota exceeded", 401),  # Should match 401 first
            ("timeout occurred due to server overload", 504),  # Should match 504 first
            # Keywords in different contexts
            ("The user has quota issues", 429),  # "quota" should match 429 (avoid "unauthorized")
            ("No time issues, just bad request", 400),  # "bad request" should match 400
            # Partial keyword matches
            ("auth-related issue", 401),  # "auth" should match
            ("rate-limited request", 429),  # "rate" should match
        ]

        for message, expected_status in edge_cases:
            result = classify_error_status_code(message)
            assert result == expected_status, f"Edge case '{message}' should classify as {expected_status}"

    def test_classify_error_status_code_performance(self):
        """Test that classification performs well with large messages."""
        # Create a large message with the keyword at the end
        large_message = "A" * 10000 + " invalid api key"
        result = classify_error_status_code(large_message)
        assert result == 401

        # Test with keyword at the beginning
        large_message = "quota exceeded " + "B" * 10000
        result = classify_error_status_code(large_message)
        assert result == 429


class TestErrorMappingIntegration:
    """Test integration scenarios with the error mapping functionality."""

    def test_representative_gemini_api_errors(self):
        """Test classification against representative real Gemini API error messages."""
        gemini_errors = [
            # Authentication errors
            ("400 API_KEY_INVALID The provided API key is invalid.", 401),
            ("401 UNAUTHENTICATED Request had invalid credentials.", 401),
            (
                "403 The caller does not have permission denied access.",
                403,
            ),  # Use "permission denied" not "PERMISSION_DENIED"
            # Rate limiting
            ("429 QUOTA_EXCEEDED Quota exceeded for requests per minute.", 429),
            ("429 RATE_LIMIT_EXCEEDED Too many requests in a short period.", 429),
            # Bad requests
            ("400 INVALID_ARGUMENT The request body is malformed.", 400),
            ("400 INVALID_REQUEST Invalid request parameters provided.", 400),
            # Service issues
            ("503 SERVICE_UNAVAILABLE The service is temporarily overloaded.", 503),
            ("503 TEMPORARILY_UNAVAILABLE Service under maintenance.", 503),
            ("504 GATEWAY_TIMEOUT The request timed out.", 504),
            ("504 Operation deadline exceeded during processing.", 504),
        ]

        for error_message, expected_status in gemini_errors:
            result = classify_error_status_code(error_message)
            assert result == expected_status, f"Gemini error '{error_message}' should classify as {expected_status}"

    def test_combined_error_messages(self):
        """Test classification with combined error messages (message + error_details)."""
        combined_messages = [
            # Simulate real combined error scenarios from the API
            ("Authentication failed invalid api key provided", 401),
            ("Request failed quota exceeded for today", 429),
            ("Service error temporarily unavailable due to maintenance", 503),
            ("Validation failed malformed input parameters", 400),
            ("Access restricted permission denied for resource", 403),
            ("Connection timeout request timed out after 30 seconds", 504),
        ]

        for message, expected_status in combined_messages:
            result = classify_error_status_code(message)
            assert result == expected_status, f"Combined message '{message}' should classify as {expected_status}"

    def test_error_mapping_coverage(self):
        """Test that error mapping covers common API error scenarios."""
        # Test at least one example for each status code in the mapping
        test_coverage = [
            (401, "unauthorized request"),
            (403, "forbidden access"),
            (429, "rate limit exceeded"),
            (400, "bad request format"),
            (503, "service unavailable"),
            (504, "timeout error"),
        ]

        for expected_status, message in test_coverage:
            result = classify_error_status_code(message)
            assert result == expected_status, f"Coverage test failed for status {expected_status}"

    def test_non_error_messages(self):
        """Test that non-error messages correctly return None."""
        non_error_messages = [
            "Operation completed successfully",
            "Request processed without issues",
            "All systems operational",
            "Data retrieved successfully",
            "No errors detected",
            "Status: OK",
        ]

        for message in non_error_messages:
            result = classify_error_status_code(message)
            assert result is None, f"Non-error message '{message}' should return None"

    def test_word_boundary_matching(self):
        """Test that word boundary matching prevents false positives."""
        # Test cases where single-word keywords should NOT match in compound words
        test_cases = [
            # "rate" should not match in "separate", "operate", "generate"
            ("Separate document processing", None),
            ("Application operates normally", None),
            ("Generate reports automatically", None),
            # "quota" should not match in other contexts
            ("Request quota for new resources", 429),  # This should match as it's a word boundary
            ("The aqueous solution failed", None),  # "quota" substring should not match
            # "auth" should not match in "author", "authorize" compound forms but avoid other keywords
            ("Author document processing", None),  # "auth" in "Author" should not match with word boundary
            ("Authorize document access", None),  # "auth" in "Authorize" should not match
            # But should match when used as a word
            ("Auth failed for user", 401),  # This should match with word boundary
            ("User auth token expired", 401),  # This should match with word boundary
        ]

        for message, expected_status in test_cases:
            result = classify_error_status_code(message)
            assert result == expected_status, f"Message '{message}' should classify as {expected_status}"
