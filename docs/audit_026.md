# Seventh audit revision 0.2.6

R7-01 was a confirmed P1 defect. R7-02 was a P2 coverage improvement: the public solver already found the correct interior maximum in its control. Both are implemented and independently checkable through validate_audit_026.

| Item | Trigger | Revised behavior |
|---|---|---|
| R7-01 | A=10^20; [A+1,A+32769]; lawful net A-u | Retained exact lower/upper violations detected; solver and ranking reject coordinate conversion error; shifted model returns -1 |
| R7-01 singleton | [A+1,A+1] | Typed precision rejection; [A,A] remains valid |
| R7-01 substituted offset | Bounds b+1 and b+32769; b a large Float | Preserve its binary rational value before substitution; do not erase offsets |
| R7-02 | u²-10^8*u^4-v² at (0,0); v fixed | Positive remaining scalar curvature fails; exact improving gain 99/10^12 |
| R7-02 controls | Concave lower/upper, strict inward derivative, flat, fixed-only | Concave/strict/fixed controls pass; flat higher-order warning remains |

Membership checks use the original retained candidate and endpoints at the supplied absolute tolerance. Endpoint conversion is conservatively rejected beyond that tolerance (default 1e-9); it is not an arbitrary-precision search feature. Solver failure propagates as BoundsPrecisionError and CLI unresolved exit 1; dependent Feasible claims record an error. A low-level required warning means complete=False even if no violation has occurred. An explicit outside candidate receives a violation as well.

All 300 previous behavior tests remain; the version assertion is updated and 27 controls are added (327 total). Source, installed wheel and core-only offline environments run all seven exporters and 27 groups. The main economic examples and 40 quadrature comparisons remain unchanged. Finite search, reduced sequential objectives, flat higher orders and >2 critical directions retain their documented limits. Technical revision acceptance is not independent audit approval, global/local optimality certification or publisher acceptance.
