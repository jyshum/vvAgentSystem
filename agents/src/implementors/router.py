def route_card(card: dict, cms_type: str, cms_config: dict) -> dict:
    """Route a single approved card to the appropriate CMS handler."""
    if cms_type == "copy_paste" or not cms_type:
        return {"status": "approved", "method": "copy_paste"}

    if cms_type == "wordpress":
        from src.implementors.wordpress_impl import apply_wordpress_change
        return apply_wordpress_change(card, cms_config)

    if cms_type == "shopify":
        from src.implementors.shopify_impl import apply_shopify_change
        return apply_shopify_change(card, cms_config)

    if cms_type == "github":
        from src.implementors.github_impl import apply_github_change
        return apply_github_change(card, cms_config)

    if cms_type == "webflow":
        from src.implementors.webflow_impl import apply_webflow_change
        return apply_webflow_change(card, cms_config)

    print(f"    Unknown cms_type '{cms_type}', falling back to copy_paste")
    return {"status": "approved", "method": "copy_paste"}
