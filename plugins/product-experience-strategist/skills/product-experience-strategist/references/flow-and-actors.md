# Flow, actors and evidence

## 3. Think end-to-end

Never optimize a screen while breaking the journey.

When relevant, check:

**Entry → prerequisites → action → validation → result → next step → recovery**

Consider only applicable states:

* first-time
* returning
* empty
* loading
* disabled
* success
* error
* cancellation
* permission denied
* expired
* interrupted
* destructive action
* recovery

For new requirements, always consider:

> What happens to existing users?

Do not assume every user enters through the new-user flow.

## 4. Model actors and permissions correctly

For multi-user products, distinguish between:

* account owner
* current user
* profile
* administrator
* parent/guardian
* child
* recipient
* payer

Do not assume:

**account = person = profile**

When sensitive actions are involved, distinguish:

**Authentication:** Who is this?

**Authorization:** Are they allowed to perform this action?

Design the flow around the actual authority model.

## 16. Evidence hierarchy

For an existing product, prefer:

1. running product behavior
2. current code/backend behavior
3. current specification
4. current design
5. historical documentation
6. assumption

Inspect available evidence rather than guessing.

If sources conflict, surface the contradiction.

Do not repeatedly inspect unchanged evidence.
