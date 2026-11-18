// The team testing guide, revision 3, as data. build_guide.js turns it into the Word document (Arial) and a Markdown copy.
// Labels in quotes are the exact words on screen in the redesigned interface. Keep them exact when the interface changes.
'use strict';

module.exports = {
  title: 'Project Nucleon: team testing guide',
  subtitle: 'Revision 3, for the redesigned interface (branch feat/ux-redesign-20261018). 18 October 2026.',
  blocks: [
    { p: 'Use this guided walkthrough to find steps that confuse you and behaviour that looks wrong. Work in order: later tasks use records from earlier ones. T1 to T3 take about 20 minutes; T1 to T9 about 60 to 75 minutes. These are estimates: write down your actual time and any help you needed.' },
    { p: 'Everything here is fictional practice data. Finishing a task is not evidence that the app is accurate for a real business or that it saves time.' },
    { box: 'warn', title: 'Shared instance rules', items: [
      'Create and change only records that carry your tag. Never edit, answer, revert or remove anyone else\'s records.',
      'Do not use the demo console, Reset, Start empty or Restore. Do not change anything under Setup.',
      'Never choose "All customers" when confirming completeness. Tick only your own customer.',
      'Before any revert or removal, read what the app says it will affect. Stop if it names anything without your tag.',
      'Replies are drafts. Nothing is sent to customers.',
      'Leave your records in place for review when you finish.'] },

    { h1: 'Before you start' },
    { h2: 'Your folder and tag' },
    { p: 'Extract Nucleon-Team-Test-Pack-v3.zip. In testers, open the folder with your name. Its CSV files already contain your tag. In this guide, TAG means that exact tag. In a pair, use one person\'s folder and tag for both roles.' },
    { table: { cols: ['Tester folder', 'TAG to use'], widths: [5000, 4000], rows: [['Hanting-HL1018U', 'HL1018U'], ['Hoang-HN1018U', 'HN1018U'], ['Phu-PD1018U', 'PD1018U'], ['Chris-CC1018U', 'CC1018U'], ['Tony-TT1018U', 'TT1018U']] } },
    { p: 'For a repeat run, copy a folder and replace its tag with a new one in all four CSV files and in everything you type. Never import another tester\'s files.' },
    { h2: 'The address, codes and version' },
    { list: [
      'Hanting gives you the address and the staff and owner access codes privately. Codes change when the app restarts. Never put a code in a screenshot, document or message.',
      'Check that you have the redesigned interface: the header shows Requests, Customers, Imports, Knowledge and Setup. If you see a single "Records" link instead, you are on the earlier version: tell Hanting and use guide revision 2.',
      'Under the header, check the line "Practice workspace with fictional data. Business date …". These examples need AUD and a business date between 16 October and 13 November 2026. If it is outside that range, ask Hanting before continuing.',
      'Write down your browser, device and window size. A desktop browser window made narrow is not a phone: say which you used.'] },
    { h2: 'How the app is organised' },
    { table: { cols: ['Area', 'What it is for', 'Who acts there'], widths: [1800, 4600, 2600], rows: [
      ['Requests', 'Customers\' requests to pay an existing invoice later. Staff send a message to the agent; the owner decides.', 'Staff send and answer; the owner decides'],
      ['Customers', 'Each customer\'s invoices, payments and credits, opening balance and completeness, notes and requests.', 'Staff and owner; only the owner confirms completeness'],
      ['Imports', 'Invoice lists and payment lists from CSV files: check, apply, keep as a draft, discard or revert.', 'Staff and owner; only the owner can say a file is complete'],
      ['Knowledge', 'Short notes the owner wants shown in requests.', 'Staff write drafts; the owner confirms'],
      ['Setup', 'Workspace type, currency and the checklist.', 'The owner. Do not change it on the shared instance'] ] } },
    { p: 'Every amount carries a mark that says how certain it is:' },
    { table: { cols: ['Mark', 'Meaning'], widths: [2000, 7000], rows: [
      ['Exact', 'Calculated from complete records, as of the date shown. Needs an opening balance with its credits stated and payment records the owner confirmed complete.'],
      ['At most', 'An upper bound: the invoice amount less the payments allocated to it. Some payments may be missing.'],
      ['Stated', 'A source said this amount was owed on a date. Payments after that date are not counted.'],
      ['Not recorded', 'No amount still owed is stated and no payment is allocated to the invoice. The invoice amount alone does not say what is still owed.'],
      ['As recorded', 'A customer balance worked out from the records entered. It is not exact unless the records are confirmed complete.']] } },
    { p: 'Times such as "18 Oct 2026, 3:38 pm" are when something was actually recorded, on the real clock. They can be later than a fixed practice business date; that is expected.' },

    { h1: 'T1  Sign in, switch roles and sign out' },
    { start: 'Signed out. A browser window where you have not signed in to Nucleon yet.' },
    { steps: [
      'Open the address. On "Sign in to Nucleon", paste the staff code into "Access code" and select "Sign in".',
      'At the top right, select "Owner". The page asks "Sign in as owner". Type the staff code on purpose and select "Sign in as owner".',
      'Now enter the owner code instead.',
      'Switch back and forth with "Staff" and "Owner". The second time, no code is asked for.',
      'Select "Staff", then "New request". Type "TAG unsent text" in "Customer\'s message". Do not send it.',
      'Select "Sign out" once.',
      'Reload the page.',
      'Sign in with the staff code and select "New request".'] },
    { checks: [
      'Step 2 shows "That is the staff code. Enter the owner code to continue as owner." and you stay on the sign-in page.',
      'Step 6 shows the sign-in page with "Signed out of owner and staff in this browser."',
      'After step 7 you are still signed out. Your partner, signed in on another browser or device, is not signed out.',
      'After step 8 "Customer\'s message" is empty. Signing out removes unsent text from this browser.',
      'Staff do not see a demo console link anywhere.'] },
    { p: 'Sign in as owner as well before T2.' },

    { h1: 'T2  Customers and invoices by hand' },
    { start: 'Signed in as staff (owner also signed in, so you can switch).' },
    { steps: [
      'Open Customers and select "Add customer". Enter "TAG Manual A fictional" and select "Add customer". You land on that customer\'s page.',
      'Select "Add invoice". The dialog names the customer; there is no customer list to pick from. Enter invoice number TAG-001, invoice date 5 October 2026, invoice amount 1000.00. Leave the due date, "Amount still owed" and "Correct as of" empty. Select "Add invoice".',
      'Go back to Customers ("← Customers" or the navigation) and add "TAG Manual B fictional".',
      'On Manual B\'s page, add invoice TAG-001 again: 5 October 2026, amount 200.00, due date 10 October 2026.',
      'Optional: open "Add invoice", type something, then press Esc. Open "Add invoice" again: what you typed is restored, with "Start again" to clear it.'] },
    { checks: [
      'Each invoice appears under its own customer. Manual A\'s due date shows "Not on record" and its "Still owed" shows "Not recorded".',
      'The same invoice number is accepted for two customers.',
      '"Correct as of" was empty when the dialog opened. If you enter an amount still owed without its date, the dialog asks for the date.'] },

    { h1: 'T3  A note, a request and a decision' },
    { start: 'T2 done. Signed in as staff and owner.' },
    { steps: [
      'As staff, open Knowledge and select "Add a note". Note: "TAG fictional test customer. Prefers a written payment date." About: TAG Manual A fictional. Kind: "Context to know". Select "Save draft".',
      'Switch to Owner. Knowledge shows that drafts wait for you. Find your note under "Waiting for the owner" and select "Confirm". Do not confirm other people\'s drafts.',
      'Switch to Staff. Open Requests, select "New request", paste: Test TAG. Could we pay invoice TAG-001 on 14 November 2026 instead?  Select "Send to the agent".',
      'Wait for "The agent needs a detail" (usually 10 to 20 seconds). Select "Send to the agent" without choosing anything first, and read the message. Then choose TAG Manual A fictional and send.',
      'When the case says "With the owner", switch to Owner and open it from Requests. Check the customer, invoice, "Key facts" and "What the owner has noted". Select "Record decision" without choosing an outcome, and read the message.',
      'Choose "Approve Sat 14 Nov". The button changes to name it. Enter the reason "Fictional test only" and record the decision.',
      'Switch to Staff, open the same case and select "Copy reply". Paste it somewhere private to check it, then delete it.',
      'In the case, select "Customer records". On the customer page, use "← Back to the request about TAG-001" to return.'] },
    { checks: [
      'Step 4 says "Choose which customer\'s invoice this is." The agent never chooses the customer for you.',
      'Step 5 says "Choose an outcome: approve the date asked for, approve a different date, or decline."',
      'The case shows "Approved. New payment date: Sat 14 Nov 2026." "Still owed" is "Not recorded" and the due date is "Not on record".',
      'The reply says "The new payment date is Saturday 14 November 2026." The button changes to "Copied". The reply is a draft: nothing is sent.',
      'Activity (a tab at the bottom of the case) says staff answered with your Manual A customer by name, not a code.',
      'Write the case address (it ends in #/case/…) in your feedback.'] },

    { h1: 'T4  Import an invoice list' },
    { start: 'Signed in as staff. Your tester folder open.' },
    { steps: [
      'Open Imports and select "Import a CSV file". Choose "Invoices". In "Where is this file from?" type "TAG Invoice test". Choose 01-invoices.csv from your folder and select "Upload and check".',
      'Under "1 Columns", check the choices: Customer, Invoice number, Invoice date, Invoice amount and Due date are matched; nothing is chosen for the amount still owed or paid.',
      'Under "Customers not in the records", set both TAG Imported customers to "Create a new customer". Never choose a Manual or sample customer. Select "Update the rows below".',
      'Under "Check the rows", compare every row with the file before applying: TAG Imported A, TAG-CSV-001, invoice date Mon 5 Oct 2026, AUD 1,000.00, due Sat 10 Oct 2026; TAG Imported B, the same number, AUD 200.00. Then select "Apply 2 rows".',
      'Import the same file again with exactly the same source "TAG Invoice test". This time select "Keep as a draft and close". On Imports, find it under "Drafts not applied" and select "Discard".',
      'Import 03-invalid-preview-only.csv as Invoices with the source "TAG Invalid preview". Read the rows, then select "Discard draft". Do not apply it.'] },
    { checks: [
      'Before step 3, "Apply" cannot be used and "Before applying" lists the unknown customers.',
      'Step 4 shows the dates and amounts above. After applying, the import shows "Applied".',
      'The second upload says "This exact file was applied before" and every row is "Already recorded".',
      'After discarding, the draft leaves "Drafts not applied" and is listed under "discarded draft" as never applied.',
      'The invalid file shows two rows "Rejected", one for the date 2026-02-31 and one for the amount 1O0.00 (letter O), and one "New" row of AUD 250.00. Nothing from it is added.',
      'In Customers, each Imported customer has exactly one TAG-CSV-001.'] },
    { note: 'Completeness is not part of this step. Only the owner can say a file makes records complete for a period, and this exercise does not do that during import.' },

    { h1: 'T5  Import payments and check allocation' },
    { start: 'T4 done. Signed in as staff.' },
    { steps: [
      'Import 02-payments.csv as "Payments received" with the source "TAG Payment test".',
      'Check the rows before applying: TAG Imported A received AUD 600.00 on Mon 12 Oct 2026 with "Allocates AUD 600.00 to TAG-CSV-001"; TAG Imported B received AUD 50.00 with no invoice. Select "Apply 2 rows".',
      'Open TAG Imported A\'s page: the Invoices tab, then the Payments tab.',
      'Open TAG Imported B\'s page, the Payments tab, and select "Allocate" on the AUD 50.00 payment. Look at the invoice list in the dialog, then select "Cancel". Do not allocate it.'] },
    { checks: [
      'Imported A\'s invoice shows "At most" AUD 400.00, with "AUD 600.00 allocated from payments". Its payment is allocated to Imported A\'s own TAG-CSV-001.',
      'Imported B\'s invoice shows "Not recorded"; its AUD 50.00 shows under "Not allocated". A payment is never moved to another customer\'s invoice with the same number.',
      'The allocation dialog offers only Imported B\'s own invoice.'] },

    { h1: 'T6  An exact amount for Imported A only' },
    { start: 'T5 done. Switch to Owner.' },
    { steps: [
      'Open TAG Imported A\'s page, tab "Opening balance". Select "Add opening balance": as at 30 September 2026; amount 0.00; "Owed by the customer"; credits "It includes none"; source "Fictional test dataset starts from zero". Select "Save opening balance".',
      'On the same tab select "Confirm completeness for TAG Imported A fictional". Leave "Only the customers ticked below" with only your Imported A ticked. Tick "Payments received". From 1 October 2026, to 16 October 2026. How you know: "Fictional test pack contains the full payment history". Read the statement, tick it, and select "Confirm completeness".',
      'Open the Invoices tab.',
      'Switch to Staff and send: Test TAG. Could we pay invoice TAG-CSV-001 on 14 November 2026 instead?  Choose TAG Imported A when asked.',
      'Switch to Owner, open the case and check the amount, dates and "Worth checking". Approve 14 November with the reason "Fictional test only". Save the case address for T7.'] },
    { checks: [
      'The opening balance shows "Entered by the owner" and the time.',
      'Imported A\'s invoice shows AUD 400.00 "Exact", as of Fri 16 Oct. Imported B stays "Not recorded" and "Not confirmed".',
      'The case shows AUD 400.00 "Exact", 6 days overdue and a 35-day extension, and says which records are confirmed complete.'] },
    { note: 'Staff can also add an opening balance; the page then shows "Entered by staff". Who should be allowed to is an open business question. In this exercise the owner enters it.' },

    { h1: 'T7  A change after the decision, and a correction' },
    { start: 'T6 done. Signed in as staff.' },
    { steps: [
      'On TAG Imported A\'s page select "Record payment or credit": "Money received", date 14 October 2026, amount 10.00, reference TAG-LATE-ENTRY. Select "Record it". Leave it not allocated.',
      'Open the Invoices tab and select "Why not exact" on TAG-CSV-001.',
      'Open the T6 case.',
      'On TAG Manual B\'s page, select "Correct" on TAG-001 (not Imported B\'s invoice). Change the amount from 200.00 to 220.00, reason "Fictional correction test", and save.'] },
    { checks: [
      'The invoice goes back to "At most". "Why not exact" says TAG-LATE-ENTRY was added inside the confirmed period after it was confirmed. The box at the top of the customer page says "1 item needs attention" and "Payment records are no longer confirmed complete: TAG-LATE-ENTRY was added". Its "Review it" button opens the Needs attention tab, which says the completeness statement no longer holds and why.',
      'The case shows "The records changed after this decision", names the payment and that staff recorded it, says the amount was exactly AUD 400.00 and is now at most AUD 400.00, and that the decision stands. Its Activity lists the change.',
      'Manual B\'s invoice shows AUD 220.00, "Corrected by staff" and "Version 2". Imported B\'s invoice is unchanged.',
      'Do not confirm completeness again in this task.'] },

    { h1: 'T8  Reverts: look first, then revert only your own test import' },
    { start: 'T7 done. Signed in as staff.' },
    { steps: [
      'Import 04-revert-only.csv as Invoices with the source "TAG Revert test". Set its one customer to "Create a new customer", update the rows and apply.',
      'On that import\'s page, read "What reverting would do". Select "Revert import…", enter "Fictional reversal test" and revert.',
      'Open Imports and select "View or revert" on your 01-invoices.csv import (the one with 2 new rows). Only read the page.',
      'Last, and only if every item it lists carries your tag: open your 02-payments.csv import and read "What reverting would do" and "Check these first". If it lists your T6 case only, revert it with the reason "Fictional dependent revert test". If it lists anything without your tag, stop and report it.'] },
    { checks: [
      'Step 2 first lists TAG-RV-001 and the TAG Revert Demo customer as marked reverted; nothing is deleted. Afterwards the import shows "Reverted" and the customer is gone from Customers.',
      'Step 3 says the import "can\'t be reverted yet" and lists what depends on it. There is no revert button, and nothing changed.',
      'Step 4 lists your decided case before you confirm, and the button reads "Revert, having checked the above". Afterwards your T6 case shows a second "records changed" note naming the reverted import.'] },

    { h1: 'T9  Phone or narrow window, and keyboard' },
    { start: 'On a phone if available; otherwise make the desktop browser window narrow and say so.' },
    { steps: [
      'Sign in. Use the bottom bar to open Requests, Customers and Imports.',
      'Open one of your customers and read an invoice row, including "Still owed".',
      'Open "Add invoice", then close it.',
      'Open your T6 case.',
      'On a computer: press Tab once on any page, then Enter on "Skip to content". Open a dialog with the keyboard and close it with Esc. In a case, move between Evidence, Activity and Technical with the arrow keys.',
      'Select "Sign out".'] },
    { checks: [
      'No page scrolls sideways. Nothing is cut off or overlapping. Tables become stacked rows with labels.',
      'In a case, the next step (decision, answer or reply) comes before the facts.',
      'After Esc, the keyboard focus goes back to the button that opened the dialog.',
      'Sign out shows the sign-in page.'] },

    { h1: 'When something seems stuck or wrong' },
    { list: [
      'Preparing normally takes 10 to 20 seconds and longer when the model is busy. You can leave the page; the case keeps preparing. If it is still preparing after two minutes, note the case address and status and tell Hanting. Do not send the same request again.',
      '"The agent needs a detail" is a question for staff, not an error.',
      '"Preparation failed" is a technical fault. Select "Prepare again" once; if it fails again, report it.',
      'A sign-in page after a restart needs the current codes, not a reset.',
      '"Sign-out not confirmed" means the app could not confirm with the server that your session ended. Your unsent text is already removed and the app stays locked. Select "Try signing out again"; if it is still not confirmed, report it with the time.',
      'If a page says it didn\'t load, use "Try again" once, then report it with the time.'] },

    { h1: 'Feedback' },
    { p: 'For each task, mark Done alone, Needed help, Blocked or Not tested. Give the time it took, including waiting.' },
    { table: { cols: ['Task', 'Result', 'Minutes', 'Help or issue'], widths: [3600, 1700, 1100, 2600], rows: [
      ['T1 Sign in, roles, sign out', '', '', ''], ['T2 Records by hand', '', '', ''], ['T3 Note, request, decision', '', '', ''], ['T4 Invoice import', '', '', ''],
      ['T5 Payment import', '', '', ''], ['T6 Exact amount', '', '', ''], ['T7 Change and correction', '', '', ''], ['T8 Reverts', '', '', ''], ['T9 Phone and keyboard', '', '', '']] } },
    { p: 'Tester, partner, TAG, date and time, device, browser and window size:' },
    { lines: 2 },
    { p: 'Which step needed help, and what wording or action did you expect?' },
    { lines: 3 },
    { p: 'Could you tell why an amount was exact, at most or not recorded, and which date it applied to?' },
    { lines: 3 },
    { p: 'What work did this remove, and what new entry or checking did it add?' },
    { lines: 3 },
    { p: 'For each problem give: task, TAG, role, steps, what you expected, what happened, the case address or invoice number, the time, and a screenshot if useful. Never include an access code. Send feedback through the team\'s usual channel and leave your test records in place.' },
  ],
};
