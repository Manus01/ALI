from app.services.metricool_client import MetricoolClient

def test_extract_connected_providers_logic():
    client = MetricoolClient()

    # Case 1: Standard socialNetworks with "Facebook" (Capitalized)
    payload_1 = {
        "socialNetworks": [
            {"id": "Facebook", "status": "connected"},
            {"id": "instagram", "status": "connected"},
            {"id": "twitter", "status": "disconnected"}
        ]
    }
    extracted_1 = client._extract_connected_providers(payload_1)
    # Expectation: Should normalize to lowercase
    assert "facebook" in extracted_1
    assert "instagram" in extracted_1
    assert "twitter" not in extracted_1

    # Case 2: Suffixes (e.g. facebookPage, instagramBusiness) - HYPOTHESIS FOR BUG
    payload_2 = {
        "socialNetworks": [
            {"id": "facebookPage", "status": "connected"},
            {"id": "linkedinPage", "status": "connected"},
            {"id": "instagramBusiness", "status": "connected"}
        ]
    }
    extracted_2 = client._extract_connected_providers(payload_2)
    
    # STRICT ASSERTION: The client MUST normalize these to the standard keys
    # specific assertions to prove failure before fix
    assert "facebook" in extracted_2, f"Failed to normalize facebookPage. Got: {extracted_2}"
    assert "linkedin" in extracted_2, f"Failed to normalize linkedinPage. Got: {extracted_2}"
    assert "instagram" in extracted_2, f"Failed to normalize instagramBusiness. Got: {extracted_2}"

    # Case 3: Flat providers list
    payload_3 = {
        "providers": ["Facebook", "LinkedIn"]
    }
    extracted_3 = client._extract_connected_providers(payload_3)
    assert "facebook" in extracted_3
    assert "linkedin" in extracted_3
