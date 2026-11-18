# Tony's questionnaire mock-up: what Nucleon takes from it (notes for the team)

21 October 2026, for the team's notes after the 1 pm meeting. It is a record the team can share, not a message to Tony.

- **Sources:** Tony's Tally form "Chatbot Questionnaire Scenario", as a teammate recorded it in [2026-10-21-tony-questionnaire.md](2026-10-21-tony-questionnaire.md), and the Lab's second iteration ([DECISIONS.md](../DECISIONS.md) E023).
- **Data:** everything below was built and tried on fictional data only.
- **Status:** nothing here is an owner rule or a team decision.

## What the mock-up contributed

The form walks an owner and an employee through a credit decision, page by page. It is honest that it is a mock-up of a flow and not a working chatbot. Three of its ideas are useful to Nucleon, and they are now in the Lab:

1. **Asking whether what the owner said earlier still holds.** The form's page 4 says: "You've last updated this relationship on the [A month ago] … Is this still the case?"
2. **Letting staff raise a concern with the owner.** The form's page 17: "You are in the process of raising a approval concern to the owner."
3. **Making it clear when the owner has to be involved.** In the form the owner confirms, gives reasons and signs.

## What Nucleon now does with those ideas

- **"Does that still hold?"** Nucleon may rely on something the owner said a while ago, or on an expectation about the future. When it does, it now asks the owner: "On Fri 16 Oct 2026 you said 'Up to 14 days this time'. Does that still hold for this request?" (an example from the fictional data).
  - The owner answers on the case page.
  - The answer is kept for that request only.
  - Until it is answered, Nucleon holds back its own suggestion.
- **Staff raise a concern.** A member of staff can say, in their own words, "I'm a bit worried about this one…".
  - Nucleon keeps the words on the case, where the owner and staff can both see them.
  - The case appears in the owner's list of things to look at "because staff raised a concern".
  - Nothing is decided, and staff do not fill in a form or give an employee ID.
- **Owner involvement is explicit.** The owner's list shows what is waiting on them. Nucleon can prepare a decision when the owner asks for one, with the owner's reason. Only the owner's Confirm button makes it a decision, and the owner can change or cancel a prepared decision first.

## What needs the team's clarification

1. **One-off or standing approval.** The form's pages 5, 7 and 12 turn one answer into a rule for the future ("make future decisions on your behalf"). Nucleon treats a yes as a decision on that one request. Should the owner be able to say a yes applies "from now on"? If so, for how long, and for what (one customer, a number of days, an amount)?
2. **The path that skips the reasons.** On page 5, answering Yes to payments past the due date skips the reasons and the signature (rule R5 in the teammate's review). Is that intended?
3. **The question set for A08.** Is the form a mock-up of a flow, the list of questions a future chatbot asks the owner (action A08 from the 15 October meeting), or both? If both, the questions probably need their own list.

## What stays future work

- **Automatic decisions on the owner's standing authority.** Not built. Nucleon prepares, and the owner confirms.
- **Periodic relationship reviews.** These are not wanted as a questionnaire. For now, Nucleon's "does that still hold?" question is asked only when a request relies on what was said.

## Assumptions we keep separate

Until there is evidence from the owner, these are working assumptions. Vince's responses are pending.

- **An extension is not a credit limit or a new order.** Agreeing to let a customer pay one invoice later does not mean approving a higher credit limit or another order. The form's pages 5 and 10 ask about going over a credit limit. Nucleon does not infer one from the other, and credit limits are outside what it handles.
- **One-off is not reusable.** A decision on one request stays with that request. Guidance for later is kept only when the owner says it should be, with the scope the owner gives.
- **"Good relationship" is context.** "Good financial terms" or "good standing" is something the owner tells Nucleon about a customer. It is not a recommendation. The form's pages 15 and 16 tell the employee to ACCEPT or DECLINE. Nucleon gives staff no such advice: only the owner decides.
