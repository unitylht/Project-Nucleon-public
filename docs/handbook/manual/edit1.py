import re, os
H = os.path.dirname(os.path.abspath(__file__))
p = open(H + '/part1.html').read()
a = p.index('<h3 id="tour-owner">')
b = p.index('<h3 id="tour-staff">')
seg = p[a:b]
parts = re.split(r'(?=<h4>)', seg)
head = parts[0]
blocks = {}
for x in parts[1:]:
    t = re.match(r'<h4>(.*?)</h4>', x).group(1)
    blocks[t] = x
# text edits
blocks['Home'] = blocks['Home'].replace('(Control panel, Review, Dashboard, Doctor)', '(Control panel, Decide, Dashboard, Doctor)')
blocks['Home'] = blocks['Home'].replace('"Mark all as read" clears the list of news.',
    '"Mark all as read" clears the list of news. The count "N need you" sits on the Decide item in the menu and is shown on every page.')
blocks['Assistant'] = blocks['Assistant'].replace('A link in the menu', 'A link in the menu, right after Home,')
blocks['Decide'] = blocks['Decide'].replace('<b>Open it:</b> every day. Press Open',
    '<b>Open it:</b> every day. The count "N need you" in the menu sits on this item. Each row shows, before you open it, the invoice, its dates, the days asked and the amount. The reason is written to you. For a hold it says which cause it is, for example "On hold: this customer is on your list of customers the agent never decides (Control panel, Advanced)". Press Open')
blocks['Requests'] = blocks['Requests'].replace('<p><b>For:</b>', '<p>Under "More" in the Owner\'s menu. <b>For:</b>', 1)
blocks['Model'] = blocks['Model'].replace('a questionnaire called "Teach it your limits" and the saved versions.',
    'a questionnaire called "Teach it your limits", a form called "Add a decision you made yourself" and the saved versions.')
blocks['Model'] += '''<p><b>Add a decision you made yourself.</b> Use it for a case you decided outside Nucleon, on the phone or in a meeting. You pick the customer. You say what was asked: more time to pay an invoice (then which invoice and how many days after its due date), or a first order on credit (then the amount and the days to pay). You say what you decided, approved or declined. You can add a few words on why. Press "Add this decision". Under the form, "Your last N answers" lists what you added and answered before.</p>
<p>Example: Bayview Gelato Co asked you by phone for 30 more days on an invoice. You declined: "Already paid late twice." Pick Bayview, pick the invoice, type 30, choose "I declined it", type the reason and press the button. From then on this case can appear among the similar cases beside a later request, with your reason, and it is a row in the model's training table marked as typed in by you.</p>
<p>It is stored like an answer to "Teach it your limits", but marked as typed in by you. It never counts in the track record. It changes no rule and no invoice.</p>
[[fig:19-model-own-decision.jpg|The form Add a decision you made yourself filled in for Bayview Gelato Co: an invoice, 30 days, declined, a short reason, and below it the opened list Your last answers.|The form filled in, and the list of your last answers opened after pressing Add this decision.]]
'''
order = ['Home', 'Assistant', 'Decide', 'Control panel', 'Dashboard', 'Customers']
more = ['Requests', 'A request page', 'Imports', 'Model', 'Knowledge', 'Setup']
out = head
for k in order:
    out += blocks[k]
    if k == 'Home':
        out += ''
out += '<h4>Under "More"</h4>\n<p>The last five pages sit under the item "More" at the end of the menu: Requests, Imports, Model, Knowledge and Setup. Press More to open them. Every address is the same as before.</p>\n[[fig:18-nav-more-open.jpg|The Owner\'s menu with the More item open, listing Requests, Imports, Model, Knowledge and Setup.|The Owner\'s menu. Home, Assistant, Decide, Control panel, Dashboard and Customers are in the bar. The other five pages are under More.]]\n'
for k in more:
    out += blocks[k]
rest = [k for k in blocks if k not in order + more]
for k in rest:
    out += blocks[k]
p = p[:a] + out + p[b:]
p = p.replace('The pages are listed in the order of the menu at the top of the screen. Owners see all of them. Staff see the first six. Quick setup and the Doctor have no menu item.',
 'The pages are listed in the order of the menu at the top of the screen. The Owner\'s bar shows Home, Assistant (only when a chat address is set up), Decide, Control panel, Dashboard and Customers. A last item, More, holds Requests, Imports, Model, Knowledge and Setup. Staff see a shorter bar: Home, Assistant, Requests and Customers, and under More: Imports, Knowledge and Setup. Quick setup and the Doctor have no menu item.')
p = p.replace('Staff see Home, Requests, Customers, Imports, Knowledge and Setup. They cannot',
 'Staff see Home, Assistant, Requests and Customers in the bar, and Imports, Knowledge and Setup under More. The count "N need you" sits on Requests. They cannot')
open(H + '/part1.html', 'w').write(p)

# settings.py
s = open(H + '/settings.py').read()
s = s.replace("('Customers the agent never decides (customer ids, separated by commas)',\n         'Every request from these customers comes to you, whatever the other rules say. The field takes customer ids, not names. Quick setup offers a list of names to tick and fills this in for you.',\n         'Hold Cityside Desserts: customer_demo_cityside. A request from Cityside then comes to you with the reason \"on hold by policy\", even for 50 dollars.',\n         'Add an id to hold a customer.',\n         'Remove an id to release a customer.',",
 "('Customers the agent never decides (their names, separated by commas)',\n         'Every request from these customers comes to you, whatever the other rules say. You type the customers\\' names, separated by commas. A name Nucleon does not know is refused before saving, with a message. Quick setup offers a list of names to tick and fills this in for you.',\n         'Type Cityside Desserts, Harbourline Catering. A request from Cityside then comes to you, even for 50 dollars. On the Decide page its row says \"On hold: this customer is on your list of customers the agent never decides\".',\n         'Add a name to hold a customer.',\n         'Remove a name to release a customer.',")
assert 'their names, separated' in s
s = s.replace("Past changes show as applied or failed.'", "Past changes show as applied or failed. A change reads, for example, \"Tue 1 Dec 2026: changes the extension rules, put back on Tue 5 Jan 2027\".'")
open(H + '/settings.py', 'w').write(s)

q = open(H + '/part3.html').read()
q = q.replace("<td>This customer is on the Owner's policy hold list</td>", "<td>This customer is on your list of customers the agent never decides</td>")
open(H + '/part3.html', 'w').write(q)
