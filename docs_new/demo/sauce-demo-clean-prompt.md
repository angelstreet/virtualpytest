# Sauce Demo - Clean Prompt (No Prior Knowledge)

## The Truly Generic Prompt (Works for Fresh Agent)

```
Automate https://sauce-demo.myshopify.com using userinterface sauce-demo2 for web devices.

Requirements to cover:
1. User can sign up with new account
2. User can login with valid credentials  
3. User can logout (complete auth lifecycle)
4. User can search for products
5. User can add products to cart
6. User can verify cart contents

Important rules:
- Entry point to home already exists
- For ALL selectors: dump_ui_elements() first to find unique #id, //xpath, or [attr]
- Selector priority: #id > //xpath > [attr] or .class > plain text (only if unique)
- For ALL input fields: click_element(field) THEN input_text(field, text)
- For ALL nodes: use 1 stable verification (form labels, buttons, unique text)
- Avoid dynamic content in verifications (product names, prices change)
- Test EACH edge after creation: execute_edge(edge_id, tree_id)

Test credentials (create during signup, reuse for login):
- Email: testuser@saucedemo.com
- Password: Test123!

Process:
1. Navigate site as anonymous user:
   - Inspect homepage, find auth links
   - Navigate to signup page, dump UI elements
   - Navigate to login page, dump UI elements
   - Find product listings, navigate to 1 product
   - Find cart link

2. Create account with test credentials:
   - Execute signup flow
   - Note: you'll be logged in after signup

3. Navigate site as authenticated user:
   - Find where logout option appears (user menu, header, account page)
   - Dump UI elements for logout

4. Find search functionality:
   - Locate search input and submit button
   - Dump UI elements for search

5. Create navigation tree:
   - Create nodes with stable verifications
   - Create edges using selectors from dump_ui_elements()
   - For each edge: execute_edge() to validate immediately

6. Create requirements with acceptance criteria

7. Create test cases linked to requirements

8. Validate end-to-end:
   - Execute at least 1 complete test case
   - Prove navigation tree works

Deliver:
- Navigation tree (all nodes reachable and tested)
- Requirements with acceptance criteria  
- Test cases with full coverage
- Proof: 1 successful test execution
```

---

## How Fresh Agent Would Use This

### Step 1: Anonymous Navigation
```
Agent: I'll navigate to the site first
→ browser_navigate(url)
→ browser_snapshot()
→ Discovers: "Log In" and "Sign up" links in header
```

### Step 2: Find Selectors
```
Agent: Let me dump UI elements to find selectors
→ dump_ui_elements()
→ Discovers: element_id="customer_login_link", text="Log In"
→ Conclusion: Use #customer_login_link (unique ID)
```

### Step 3: Create Nodes with Stable Verifications
```
Agent: What's unique and stable on login page?
→ browser_snapshot() on /account/login
→ Sees: "Forgot your password?" link (only on login page)
→ Verification: "Forgot your password?" (stable structural element)
```

### Step 4: Create Edge and Test
```
Agent: Create home → login edge
→ create_edge(actions=[click_element("#customer_login_link")])
→ execute_edge() to validate
→ If fails: adjust selector and retry
```

### Step 5: Complete Auth Flow
```
Agent: Need to find logout after logging in
→ Execute signup with test credentials
→ Now logged in, take snapshot
→ Discovers: User menu in header with logout option
→ Create logout edge
```

## Why This Works Without Prior Knowledge

1. **Discovery-driven**: Forces agent to explore and dump UI
2. **Validation-driven**: Tests edges immediately, catches errors
3. **Principle-based**: Teaches "why" (stability, uniqueness) not "what" (specific selectors)
4. **Complete flow**: Ensures logged OUT and logged IN exploration
5. **Proof required**: Must execute end-to-end test

---

## Even Shorter Version (30 seconds to read)

```
Automate https://sauce-demo.myshopify.com (sauce-demo, web)

Cover: signup, login, logout, search, add-to-cart, verify cart

Rules:
1. dump_ui_elements() first → use #id or //xpath
2. Click inputs before typing
3. Test each edge: execute_edge() after creation
4. Stable verifications: form labels, buttons (not product names)
5. Navigate logged OUT then logged IN (find logout)

Credentials: testuser@saucedemo.com / Test123!

Process: Navigate → Dump → Create nodes/edges → Test edges → Requirements → Test cases → Execute 1 test

Deliver: Complete tree + requirements + test cases + execution proof
```
