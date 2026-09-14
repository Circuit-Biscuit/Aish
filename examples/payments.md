# Session log: payments reliability investigation

I spent this session investigating duplicate charges in the payments module.

The retry wrapper lives in packages/payments/src/charge/retryWrapper.ts. It wraps
the outbound call to the vendor charge endpoint. The wrapper retries three times
with a 200ms backoff. Critically, it does not send an idempotency key, and the
endpoint it calls is a non-idempotent POST. I confirmed by replaying traffic in
the sandbox that two charges land when the first response times out.

The same retry wrapper is also used by packages/payments/src/refund/refundClient.ts,
which calls the vendor refund endpoint. That path has the same defect, so refunds
can also double-apply. Nobody has reported it, probably because refund volume is low.

I checked the vendor documentation. The vendor supports an Idempotency-Key header on
both the charge endpoint and the refund endpoint. So the fix is available on both paths.

I looked at packages/payments/src/ledger/reconcile.ts because I wanted to know whether
duplicates would be caught downstream. Reconciliation only compares daily totals, so a
duplicate charge inside the same day is invisible to it. That means we have no detection.

I tried adding the idempotency key directly in the retry wrapper, but the wrapper does
not know the business-level operation identity, so the key would be per-attempt rather
than per-operation, which defeats the purpose. I reverted that change.

The correct fix is for the caller to pass a stable operation key into the wrapper.
That requires changing the signature of the wrapper and updating both call sites.

This is a live money path, so it needs owner sign-off before merging. The owner of the
payments module is the platform team.

I am not certain whether duplicates already exist in production. Retry shipped in
version 4.2, which was three months ago. Someone should query the ledger for pairs of
charges with the same amount and customer within sixty seconds of each other.

Do not change the error string "charge_declined_retryable" that the vendor returns,
because the mobile client matches on it exactly.
