# Web Automation Prompt (AI Exploration)

Automate [URL] for userinterface [USERINTERFACE_NAME] on web/desktop devices.

**Device Model**: `host_vnc` or `web`

**Requirements to cover:**
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]
...

---

## Process

### PHASE 1: Setup & AI Exploration (AUTOMATED)

**1. Get compatible host/device:**
```python
hosts = get_compatible_hosts(userinterface_name='[USERINTERFACE_NAME]')
host_name = hosts['recommended_host']
device_id = hosts['recommended_device']
```

**2. Start AI exploration:**
```python
result = start_ai_exploration(
  userinterface_name='[USERINTERFACE_NAME]',
  original_prompt='Build navigation for [SITE_TYPE: e-commerce/social/streaming/etc.]'
)
exploration_id = result['exploration_id']
```

AI analyzes home screen and proposes:
- Strategy: `click` (web elements)
- Items: Login, signup, search, products, etc.
- Selectors: CSS (#id, .class) and XPath (//button[@type='submit'])

**3. Approve and create structure:**
```python
approve_exploration_plan(
  exploration_id=exploration_id,
  host_name=host_name,
  userinterface_name='[USERINTERFACE_NAME]',
  selected_items=['login', 'signup', 'search', 'product_detail', 'cart']  # Customize
)
```

AI creates:
- Nodes for each screen
- Bidirectional edges with click_element + BACK
- Proper selectors (prioritizes #id > XPath > text)

**4. Validate all edges:**
```python
while True:
  result = validate_exploration_edges(
    exploration_id=exploration_id,
    host_name=host_name,
    userinterface_name='[USERINTERFACE_NAME]'
  )
  
  print(f"✅ {result['item']}: {result['click_result']}")
  
  if not result.get('has_more_items'):
    break
```

AI tests each edge:
- home → login: click #customer_login_link
- login → home: BACK
- Captures screenshots as proof

**5. Get and apply verifications:**
```python
suggestions = get_node_verification_suggestions(
  exploration_id=exploration_id,
  host_name=host_name
)

approve_node_verifications(
  exploration_id=exploration_id,
  host_name=host_name,
  userinterface_name='[USERINTERFACE_NAME]',
  approved_verifications=suggestions['suggestions']
)
```

**6. Finalize tree:**
```python
nodes = list_navigation_nodes(userinterface_name='[USERINTERFACE_NAME]')
tree_id = nodes['tree_id']

finalize_exploration(
  exploration_id=exploration_id,
  host_name=host_name,
  tree_id=tree_id
)
```

---

### PHASE 2: State-Dependent Flows (MANUAL)

**7. Handle authenticated states:**

Common patterns requiring manual handling:
- **Logout**: Only visible after login
- **User menu**: Appears after authentication
- **Cart**: Populated after add-to-cart action
- **Search results**: Require search input first

Example - Logout flow:
```python
# a. Navigate to login, perform login to discover logout location
navigate_to_node(
  userinterface_name='[USERINTERFACE_NAME]',
  target_node_label='login'
)

# b. Fill login form (manual action - not part of navigation tree)
execute_device_action(
  actions=[
    {'command': 'click_element_by_id', 'params': {'element_id': 'email_field', 'wait_time': 500}},
    {'command': 'input_text', 'params': {'selector': '#email_field', 'text': 'test@example.com', 'wait_time': 500}},
    {'command': 'click_element_by_id', 'params': {'element_id': 'password_field', 'wait_time': 500}},
    {'command': 'input_text', 'params': {'selector': '#password_field', 'text': 'Password123!', 'wait_time': 500}},
    {'command': 'click_element', 'params': {'text': 'Login', 'wait_time': 2000}}
  ]
)

# c. Inspect page to find logout element
elements = dump_ui_elements(device_id=device_id, host_name=host_name, platform='web')

# d. Analyze for logout selector
action = analyze_screen_for_action(
  elements=elements['elements'],
  intent='logout button',
  platform='web'
)

# e. Create logout node and edge
create_node(tree_id=tree_id, label='logout', type='Screen')

create_edge(
  tree_id=tree_id,
  source_node_id='home',  # Or wherever logout appears
  target_node_id='logout',
  source_label='home',
  target_label='logout',
  action_sets=[{
    'id': 'home_to_logout',
    'label': 'home → logout',
    'actions': [action],  # From analyze_screen_for_action
    'retry_actions': [],
    'failure_actions': []
  }, {
    'id': 'logout_to_home',
    'label': 'logout → home',
    'actions': [{'command': 'press_key', 'params': {'key': 'BACK', 'wait_time': 1000}}],
    'retry_actions': [],
    'failure_actions': []
  }]
)

# f. Test edge
execute_edge(edge_id='edge-...', tree_id=tree_id, userinterface_name='[USERINTERFACE_NAME]')
```

---

### PHASE 3: Requirements & Test Cases

**8. Create requirements:**
```python
create_requirement(
  requirement_code='REQ_AUTH_001',
  requirement_name='User can login with valid credentials',
  description='Users must authenticate with email and password',
  priority='P1',
  category='authentication'
)
```

**9. Create test cases:**
```python
generate_and_save_testcase(
  prompt='Navigate to login, verify login form, navigate back to home',
  testcase_name='TC_AUTH_01_LoginNavigation',
  userinterface_name='[USERINTERFACE_NAME]',
  host_name=host_name,
  device_id=device_id,
  description='Validates login navigation flow',
  folder='authentication',
  tags=['auth', 'navigation']
)
```

**10. Link to requirements:**
```python
link_testcase_to_requirement(
  testcase_id='[TESTCASE_ID]',
  requirement_id='[REQUIREMENT_ID]',
  coverage_type='full'
)
```

**11. Execute end-to-end test:**
```python
execute_testcase(
  testcase_name='TC_AUTH_01_CompleteAuthFlow',
  host_name=host_name,
  device_id=device_id,
  userinterface_name='[USERINTERFACE_NAME]'
)
```

**12. Verify coverage:**
```python
summary = get_coverage_summary()
print(f"Coverage: {summary['coverage_percentage']}%")
```

---

## Web-Specific Best Practices

### 1. Selector Priority (AI handles automatically)
1. **#id** - Always unique, fastest
2. **//xpath** - For buttons, forms: `//button[@type='submit']`
3. **.class** - Verify uniqueness with dump_ui_elements
4. **text** - Fallback, slower

### 2. Input Pattern (AI handles automatically)
```
ALWAYS: click_element → input_text
```

Example:
```python
[
  {'command': 'click_element_by_id', 'params': {'element_id': 'search-field', 'wait_time': 500}},
  {'command': 'input_text', 'params': {'selector': '#search-field', 'text': 'query', 'wait_time': 500}},
  {'command': 'click_element', 'params': {'text': 'Search', 'wait_time': 2000}}
]
```

### 3. Wait Times
- Click element: 1000ms
- Input text: 500ms
- Submit/Navigate: 2000ms

### 4. Verification Strategy
Use **stable structural elements**:
- ✅ Form labels: "First Name", "Email Address"
- ✅ Headings: "My Cart", "Account Settings"
- ✅ Unique text: "Forgot your password?"
- ❌ Dynamic content: Product names, prices, dates

---

## Common Web Patterns

### E-commerce Site
**Nodes**: home, login, signup, logout, search, product_detail, cart, checkout

**Example edges**:
- home → login: click #customer_login_link
- home → search: click .search-input, input text, click submit
- product_detail → cart: click "Add to Cart", click cart icon

### SaaS App
**Nodes**: home, login, dashboard, settings, profile, logout

**Example edges**:
- home → login: click "Sign In"
- dashboard → settings: click settings icon
- settings → dashboard: BACK or click "Dashboard"

### Content Site
**Nodes**: home, article, category, search, author_profile

**Example edges**:
- home → category: click category link
- category → article: click article title
- article → author_profile: click author name

---

## Troubleshooting

### Edge validation fails
1. Check selector uniqueness:
   ```python
   elements = dump_ui_elements(device_id=device_id, host_name=host_name, platform='web')
   # Verify element appears only once
   ```

2. Re-analyze for better selector:
   ```python
   action = analyze_screen_for_action(
     elements=elements['elements'],
     intent='[ELEMENT_DESCRIPTION]',
     platform='web'
   )
   ```

3. Update edge:
   ```python
   update_edge(
     tree_id=tree_id,
     edge_id='[EDGE_ID]',
     action_sets=[...]  # New actions
   )
   ```

### Verification false positives
- Use **structural elements** (form fields, headings)
- Avoid **dynamic content** (product names, dates)
- Verify uniqueness with dump_ui_elements

### BACK navigation doesn't work
- Some SPAs use browser history, BACK works
- Some use route changes, need explicit navigation
- Test and adjust based on site behavior

---

## Time Estimate

**For typical web app (7 nodes, 14 edges):**
- Phase 1 (AI Exploration): 10-15 minutes
- Phase 2 (Manual state flows): 15-30 minutes
- Phase 3 (Requirements & tests): 1 hour
- **Total: ~1.5-2 hours**

**vs. Manual: 4-5 hours**

**Time Saved: ~60-67%**

---

## Example: E-commerce Site

```python
# Complete workflow for sauce-demo.myshopify.com

# 1. Setup
hosts = get_compatible_hosts(userinterface_name='sauce-demo')

# 2. AI builds tree
result = start_ai_exploration(
  userinterface_name='sauce-demo',
  original_prompt='Build e-commerce navigation'
)

# 3. Approve (login, signup, search, products, cart)
approve_exploration_plan(
  exploration_id=result['exploration_id'],
  host_name=hosts['recommended_host'],
  userinterface_name='sauce-demo',
  selected_items=['login', 'signup', 'search', 'product_detail', 'cart']
)

# 4. Validate
while validate_exploration_edges(...)['has_more_items']: pass

# 5. Add verifications
suggestions = get_node_verification_suggestions(...)
approve_node_verifications(approved_verifications=suggestions['suggestions'])

# 6. Finalize
finalize_exploration(...)

# 7. Manual: Add logout (after login)
# ... (see PHASE 2 above)

# 8. Requirements & test cases
# ... (see PHASE 3 above)

# Done! ✅
```

---

**Recommendation**: Use AI Exploration for 90% of web automation. Manual tools only for edge cases.

