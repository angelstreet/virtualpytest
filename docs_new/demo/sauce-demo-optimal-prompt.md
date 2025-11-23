# Optimal Prompt for Sauce Demo Automation

## The Perfect Prompt (AI Exploration Version - RECOMMENDED)

```
Automate https://sauce-demo.myshopify.com using userinterface sauce-demo for web devices.

Requirements to cover:
1. User can sign up with new account
2. User can login with valid credentials  
3. User can logout (complete auth lifecycle)
4. User can search for products
5. User can add products to cart
6. User can verify cart contents

Process:

**PHASE 1: Setup & AI Exploration (AUTOMATED)**

1. Get compatible host and device:
   hosts = get_compatible_hosts(userinterface_name='sauce-demo')
   host_name = hosts['recommended_host']
   device_id = hosts['recommended_device']

2. Start AI exploration (analyzes home screen):
   result = start_ai_exploration(
     userinterface_name='sauce-demo',
     original_prompt='Build e-commerce navigation for sauce-demo'
   )
   exploration_id = result['exploration_id']
   
   Review AI-proposed items: login, signup, search, products, cart, etc.

3. Approve and create structure:
   approve_exploration_plan(
     exploration_id=exploration_id,
     host_name=host_name,
     userinterface_name='sauce-demo',
     selected_items=['login', 'signup', 'search', 'product_detail', 'cart']
   )
   
   AI creates all nodes and edges automatically with correct selectors.

4. Validate all edges sequentially:
   while True:
     result = validate_exploration_edges(
       exploration_id=exploration_id,
       host_name=host_name,
       userinterface_name='sauce-demo'
     )
     
     if not result.get('has_more_items'):
       break
   
   AI tests each edge automatically:
   - home → login: click #customer_login_link
   - login → home: BACK
   - home → signup: click signup link
   - etc.

5. Get and apply verifications:
   suggestions = get_node_verification_suggestions(
     exploration_id=exploration_id,
     host_name=host_name
   )
   
   approve_node_verifications(
     exploration_id=exploration_id,
     host_name=host_name,
     userinterface_name='sauce-demo',
     approved_verifications=suggestions['suggestions']
   )

6. Finalize tree:
   nodes = list_navigation_nodes(userinterface_name='sauce-demo')
   tree_id = nodes['tree_id']
   
   finalize_exploration(
     exploration_id=exploration_id,
     host_name=host_name,
     tree_id=tree_id
   )

**PHASE 2: Auth Flow Completion (MANUAL - For States Not Visible on Home)**

7. Manual signup/login to discover logout:
   - Navigate to signup node
   - Fill form with test credentials (testuser@saucedemo.com / Test123!)
   - Login to discover logged-in state
   - Find logout element location

8. Create logout node manually:
   create_node(
     tree_id=tree_id,
     label='logout',
     type='Screen'
   )
   
   create_edge(
     tree_id=tree_id,
     source_node_id='home',
     target_node_id='logout',
     source_label='home',
     target_label='logout',
     action_sets=[...]  # Based on discovered logout location
   )
   
   execute_edge(edge_id='...', tree_id=tree_id)

**PHASE 3: Requirements & Test Cases (AFTER ALL EDGES VALIDATED)**

9. Create 6 requirements with acceptance criteria

10. Create 6 test cases linked to requirements

11. Execute TC_AUTH_01_CompleteAuthFlow end-to-end to validate

12. Verify all test cases pass

Deliver:
- Navigation tree: 7 nodes (home, signup, login, logout, product_detail, cart, search_results)
- 6 requirements with acceptance criteria  
- 6 test cases with full coverage
- Proof: Execute TC_AUTH_01 successfully (signup → login → logout → login)
```

---

## Why AI Exploration Is Better

### Manual vs AI Comparison:

| Task | Manual Approach | AI Exploration |
|------|----------------|----------------|
| **Screen Analysis** | Visual inspection + trial/error | Automatic AI analysis |
| **Find Selectors** | dump_ui_elements + manual search | AI selector scoring |
| **Create Nodes** | 1 at a time | Batch creation |
| **Create Edges** | 1 at a time + test | Batch creation + auto-test |
| **Test Edges** | Manual execute_edge per edge | Sequential auto-validation |
| **Add Verifications** | Manual inspection | AI suggestions |
| **Time for 5 nodes** | ~2-3 hours | ~10-15 minutes |
| **Error Rate** | High (selector ambiguity) | Low (AI validates uniqueness) |

**Time Saved: ~90%** for typical apps

---

## When to Use AI vs Manual

| Scenario | Use |
|----------|-----|
| **Initial home screen navigation** | ✅ AI Exploration (login, signup, search, etc.) |
| **Dynamic state discovery** | ⚠️ Manual (logout after login, cart after add) |
| **TV dual-layer** | ✅ AI Exploration (handles automatically) |
| **Complex custom flow** | ⚠️ Manual (full control) |
| **Edge fix** | ⚠️ Manual (update_edge) |

**Best Practice:** Use AI for initial exploration, manual for state-dependent flows.

---

## Estimated Time Comparison

**Manual Approach (Original Prompt):**
- Phase 1: Setup & Discovery: 30 min
- Phase 2: Build tree manually (7 nodes, 14 edges): 2 hours
- Phase 3: Test each edge individually: 30 min
- Phase 4: Add verifications: 30 min
- Phase 5: Requirements & test cases: 1 hour
- **Total: ~4.5 hours**

**AI Exploration Approach (New Prompt):**
- Phase 1: AI exploration (setup → analysis → approval → validation): 15 min
- Phase 2: Manual logout flow: 15 min
- Phase 3: Requirements & test cases: 1 hour
- **Total: ~1.5 hours**

**Time Saved: 67%** 

---

## Manual Fallback (If AI Not Available)

<details>
<summary>Click to expand manual prompt</summary>

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
- Test EACH edge after creation: execute_edge(edge_id, tree_id) - MANDATORY

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

**PHASE 1: Setup & Discovery (DO THIS FIRST)**

0. Get compatible host and device:
   hosts = get_compatible_hosts(userinterface_name='sauce-demo')
   host_name = hosts['recommended_host']
   device_id = hosts['recommended_device']

1. Get tree_id for execute_edge() calls:
   nodes = list_navigation_nodes(userinterface_name='sauce-demo')
   # Note the tree_id from response - needed for all edge testing

2. Navigate site logged OUT: inspect signup (#customer_register), login (#customer_login_link)

3. Create signup account with test credentials

4. Navigate site logged IN: find logout element location

5. Dump UI elements for all screens to get exact selectors:
   dump_ui_elements(device_id=device_id, host_name=host_name, platform='web')

**PHASE 2: Build Navigation Tree (ONE EDGE AT A TIME - TEST IMMEDIATELY)**

6. For EACH node/edge pair, follow this sequence:

   a. Analyze selectors BEFORE creating edge:
      elements = dump_ui_elements(device_id=device_id, host_name=host_name, platform='web')
      
      action = analyze_screen_for_action(
        elements=elements['elements'],
        intent='login button',
        platform='web'
      )
      
      # Use action['command'] and action['action_params'] in create_edge
   
   b. Create node:
      create_node(tree_id='...', label='login', type='Screen')
   
   c. Create edge with analyzed selectors:
      create_edge(
        tree_id='...',
        source_node_id='home',
        target_node_id='login',
        source_label='home',
        target_label='login',
        action_sets=[{
          'id': 'home_to_login',
          'label': 'home → login',
          'actions': [action],  # From analyze_screen_for_action
          'retry_actions': [],
          'failure_actions': []
        }]
      )
   
   d. TEST EDGE IMMEDIATELY (MANDATORY):
      execute_edge(edge_id='...', tree_id='...', userinterface_name='sauce-demo')
   
   e. If fails: update_edge() with correct selectors, repeat step d
   
   f. If success: Move to next node/edge pair
   
   DO NOT create multiple edges without testing each one.

   Example edges to create (in order):
   - home → signup: click_element("#customer_login_link") then click "Sign up"
   - home → login: click_element("#customer_login_link")
   - login → home (after login): verify redirect
   - home → logout: click user menu, click logout link
   - home → search: click_element(".search-input"), input_text(".search-input", "jacket"), click submit
   - home → product: click_element("Grey jacket")
   - product → cart: click_element("Add to Cart"), click_element(".checkout-link")

**PHASE 3: Requirements & Test Cases (AFTER ALL EDGES VALIDATED)**

7. Create 6 requirements with acceptance criteria

8. Create 6 test cases linked to requirements

9. Execute TC_AUTH_01_CompleteAuthFlow end-to-end to validate

10. Verify all test cases pass

Deliver:
- Navigation tree: 7 nodes (home, signup, login, logout, product_detail, cart, search_results)
- 6 requirements with acceptance criteria  
- 6 test cases with full coverage
- Proof: Execute TC_AUTH_01 successfully (signup → login → logout → login)
```
</details>

---

## Template for Any E-commerce Site

### AI Exploration Template:

```python
# Step 1: Setup
hosts = get_compatible_hosts(userinterface_name='YOUR_UI_NAME')

# Step 2: AI analyzes and builds
result = start_ai_exploration(
  userinterface_name='YOUR_UI_NAME',
  original_prompt='Build navigation for [YOUR_SITE_TYPE]'
)

# Step 3: Approve
approve_exploration_plan(exploration_id=result['exploration_id'], ...)

# Step 4: Validate
while validate_exploration_edges(...)['has_more_items']: pass

# Step 5: Finalize
finalize_exploration(...)

# Step 6: Handle dynamic states manually (if needed)
# - Logout after login
# - Cart after add to cart
# - etc.
```

Replace:
- `YOUR_UI_NAME` with your userinterface name
- `YOUR_SITE_TYPE` with site description (e-commerce, social, streaming, etc.)

The AI handles:
- Selector discovery
- Node creation
- Edge creation
- Validation
- Verifications

You handle:
- State-dependent flows (logout, cart, etc.)
- Custom complex flows

---

## Key Improvements Over Manual

1. **No Selector Guessing**: AI analyzes screen and scores selectors
2. **Batch Creation**: All nodes/edges created at once
3. **Auto-Validation**: Tests all edges sequentially
4. **AI Verifications**: Suggests unique verifications per node
5. **TV Support**: Handles dual-layer automatically (focus + screen nodes)
6. **Error Prevention**: Validates selector uniqueness before creating edges

**Recommendation**: Always start with AI Exploration. Only use manual tools for edge cases or fixes.
