# NYC case-study visual review

The figure-only redesign preserves the current corrected-V2 master structure: local NYC road context and route overlays remain in panel (a), while panel (b) retains the aligned upper score profiles and lower selected-path profile. The source query remains `NYC-Q012-MORNING-R20` with the stored budget (B=8.382654224124) min, the recorded route geometry, and the audited eight-cell profile.

## Review checks

1. **Preserved from the current figure:** source/destination, local road network, P1–P5 route overlays, fastest-path reference, score profiles, interval-best departure at 07:53 on P3, temporal boundaries, scores, and travel times.
2. **Improved using the profile-strip design:** the lower ribbon now allocates more height to the selected profile, uses compact path/score labels for ordinary intervals, and reserves callouts for the unusual singleton events.
3. **Singleton event cells explicitly distinguished:** YES. The three isolated cells at 07:41, 07:58, and 07:59 are rendered as path-colored diamonds at their exact departure times.
4. **Path colors consistent across map, score plot, and ribbon:** YES. P1–P5 use one stable path-specific palette across both panels.
5. **Interval-best visually separate from path-colored elements:** YES. Its vertical guide, marker, legend entry, and annotation use neutral dark gray rather than P3 green.
6. **Readable at double-column scale:** YES. The background network is subdued, the map legend is compact, and the lower profile receives approximately 38% of panel (b)'s height.

The compact profile summary reports the audited structure: `8 temporal cells · 5 selected paths · 3 singleton cells`. No experiment, query, frozen artifact, manuscript LaTeX, score, travel-time value, or temporal boundary was modified.

CASE_STUDY_FIGURE_READY = true
