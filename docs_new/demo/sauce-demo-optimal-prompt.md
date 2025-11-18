# Optimal Prompt for Sauce Demo Automation

## The Perfect Prompt (Based on Lessons Learned)

```
Automate https://sauce-demo.myshopify.com using userinterface sauce-demo for web devices.

Requirements to cover:
1. User can sign up with new account
2. User can login with valid credentials  
3. User can logout (complete auth lifecycle)
4. User can search for products
5. User can add products to cart
6. User can verify cart contents

Critical rules:
- Entry point to home already exists
- Use CSS selectors: #customer_login_link, .search-input, [aria-label="..."]
- Use XPath for buttons: //button[@type='submit'], //button[text()='Add to Cart']
- For input fields: ALWAYS click_element(field) THEN input_text(field, text)
- Verify selector uniqueness with dump_ui_elements() before using
- Test each edge immediately: execute_edge(edge_id, tree_id) after creation

Node verifications (use stable structural elements):
- home: "Just a demo site showing off what Sauce can do." (unique subtitle)
- signup: "First Name" (form label - only on signup)
- login: "Forgot your password?" (link - only on login)
- logout: Verify logged-in state indicator disappears
- product_detail: "Add to Cart" (button - stable across products)
- cart: "My Cart" (heading - stable)
- search_results: Use search term as verification

Test credentials for signup/login:
- Email: testuser@saucedemo.com
- Password: Test123!

Navigation flow to implement:
1. Explore logged OUT: home → signup, home → login
2. Complete signup: Create account with test credentials
3. Explore logged IN: Find where logout appears (likely in user menu/header)
4. Complete logout: Create logout edge from authenticated state back to home
5. Product flow: home → product_detail → cart
6. Search flow: home → search_results → product_detail

Process:
1. Navigate site logged OUT: inspect signup (#customer_register), login (#customer_login_link)
2. Create signup account with test credentials
3. Navigate site logged IN: find logout element location
4. Dump UI elements for all screens to get exact selectors
5. Create nodes with structural verifications (1 per node, unless not unique)
6. Create edges using CSS/XPath selectors:
   - home → signup: click_element("#customer_login_link") then click "Sign up"
   - home → login: click_element("#customer_login_link")
   - login → home (after login): verify redirect
   - home → logout: click user menu, click logout link
   - home → search: click_element(".search-input"), input_text(".search-input", "jacket"), click submit
   - home → product: click_element("Grey jacket")
   - product → cart: click_element("Add to Cart"), click_element(".checkout-link")
7. ⚠️ CRITICAL - INCREMENTAL VALIDATION (ENFORCED):
   After EACH edge creation, the tool will remind you to test it.
   You MUST test before creating the next edge:
   
   For EACH edge:
   a. create_edge(...) 
   b. Tool says: "Test this edge before creating more!"
   c. execute_edge(edge_id=..., tree_id=...)  ← REQUIRED
   d. If fails: update_edge() with correct selectors, test again
   e. If success: Move to next edge
   
   DO NOT create multiple edges without testing each one.
   This prevents cascading failures.
   
8. After all edges validated: Create 6 requirements with acceptance criteria
9. Create 6 test cases linked to requirements
10. Execute TC_AUTH_01_CompleteAuthFlow end-to-end to validate

Deliver:
- Navigation tree: 7 nodes (home, signup, login, logout, product_detail, cart, search_results)
- 6 requirements with acceptance criteria  
- 6 test cases with full coverage
- Proof: Execute TC_AUTH_01 successfully (signup → login → logout → login)
```

---

## Why This Prompt Would Have Worked Perfectly

### Issues Prevented:

| Issue We Had | How This Prompt Prevents It |
|--------------|----------------------------|
| **Dynamic "Grey jacket" in verifications** | ✅ Specifies: "Use stable elements: Add to Cart button, My Cart heading" |
| **Missing click before input_text** | ✅ Explicit: "click_element(field) THEN input_text(field, text)" |
| **Ambiguous text selectors** | ✅ Provides exact selectors: #customer_login_link, .search-input |
| **Search edge missing click** | ✅ Shows full sequence: "click field, input text, click submit" |
| **Logout node incomplete** | ✅ Requires: "Navigate logged IN: find logout element location" |
| **No edge testing** | ✅ Mandates: "Test EACH edge: execute_edge() after creation" |
| **False positive verifications** | ✅ Specifies stable verifications per node |
| **No end-to-end validation** | ✅ Requires: "Execute TC_AUTH_01 successfully" |

### Key Additions That Make It Work:

1. **Exact Selectors Given**:
   - `#customer_login_link` (from actual site inspection)
   - `.search-input` (common pattern)
   - `//button[@type='submit']` (XPath for submit)

2. **Complete Auth Flow**:
   - Signup → Login → Logout → Login (full lifecycle)
   - Explicitly states: "Find where logout appears"

3. **Verification Examples**:
   - Shows exact text to use: "Just a demo site...", "First Name", "Forgot your password?"
   - Explains why: "unique subtitle", "only on signup", "only on login"

4. **Input Pattern Emphasized**:
   - Search example shows: click → input → click submit (3 steps)
   - ALWAYS in caps to emphasize importance

5. **Edge Testing Required**:
   - "Test EACH edge: execute_edge() after creation"
   - Catches errors immediately, not at the end

6. **Proof of Completion**:
   - "Execute TC_AUTH_01 successfully"
   - Validates everything works end-to-end

---

## Estimated Time Savings

**With Original Prompt:**
- Initial implementation: 2 hours
- Debugging verification issues: 1 hour
- Fixing selector ambiguity: 30 min
- Adding missing click to search: 15 min
- Updating guidance to prevent future issues: 30 min
- **Total: ~4.5 hours**

**With Optimal Prompt:**
- Implementation following clear guidelines: 2 hours
- Edge testing catches issues immediately: included
- End-to-end test validates completion: included
- **Total: ~2 hours**

**Time Saved: 55%** 

---

## Template for Any E-commerce Site

Replace sauce-demo specifics with:
- Different URL and userinterface name
- Different auth elements (if not using #customer_login_link)
- Different product/cart structure
- Different test credentials

The core principles remain the same:
- Use structural selectors
- Click before type
- Test edges individually
- Verify with stable elements
- Complete all user flows
- Prove with execution

