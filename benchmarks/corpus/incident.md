Postmortem for the checkout outage on the fourteenth.

A config change set the connection pool maximum to 5, down from 50. That was a
typo in the values file. The change deployed at 14:02. Within four minutes the
checkout service saturated its pool, so requests queued. Queue depth passed the
health check timeout, so the load balancer marked instances unhealthy and
removed them. That concentrated traffic on the remaining instances, which
saturated faster. The service was fully down by 14:11.

We rolled back at 14:31 and recovery was complete by 14:34. Total user impact
was 32 minutes.

Detection was slow because the pool saturation metric exists but has no alert.
The first signal was a customer report.

The rollback was slow because the deploy tool requires manual approval and the
approver was in a meeting.

Action items: add an alert on pool saturation, add a validation rule that
rejects pool sizes under 10, and allow rollback without approval during an
active incident.
