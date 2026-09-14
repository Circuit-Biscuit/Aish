On why we are not adopting the new scheduler.

The proposal is technically sound and the benchmarks are real. My hesitation is
about timing rather than merit. We are three weeks from a release that already
carries two risky changes, and the scheduler touches the same code paths as one
of them. Landing it now means that if the release regresses, we will not know
which of the three changes caused it, and bisecting across a scheduler rewrite
is considerably harder than bisecting across the other two.

There is also a staffing argument. The person who understands the current
scheduler best is on leave until the middle of next month. If something subtle
breaks, we would be debugging unfamiliar code without the one person who could
shortcut it.

None of this is an argument against the design. I would like to land it in the
release after next, with the other two changes already shipped and observed in
production for a few weeks, and with the original author back to review.

If the team disagrees I will not block it, but I would want us to at least
commit to a rollback plan that does not require a full redeploy.
