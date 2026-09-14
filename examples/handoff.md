# Handoff notes

I've been working on the authentication refresh bug in the checkout service.

The main problem is that in src/auth/session.py, around line 140, the token
refresh runs before the clock skew check. When the client's clock is more than
30 seconds ahead of the server, the refresh sends an already-expired token,
which the gateway rejects with a 401. The client then retries, which triggers
another refresh, and this loops indefinitely.

I confirmed this by reproducing it locally with the clock set forward. It
happens every time, so it is not a flaky test.

I tried moving the retry limit down to 3 attempts, but that just masks the
problem — the user still gets logged out, it just happens faster. I have
reverted that change.

I think the right fix is to move the skew check above the refresh call, but I
have not verified that this does not break the offline-mode path, which also
calls into the same function. Someone should check that before merging.

Also worth noting: the error string the gateway returns is exactly
"token_expired_at_issue" — do not change it, the mobile client matches on it.

One thing I am unsure about is whether the staging gateway has the same skew
tolerance as production. That needs checking.
