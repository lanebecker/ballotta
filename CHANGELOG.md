# Changelog

All notable changes to Ballotta (https://ballotta.org) are recorded here, newest first.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), plus a "Tests" section where the checks
changed. Versions follow [Semantic Versioning](https://semver.org/) as the README's "Versioning" section applies it.

`VERSION` is the one source of truth for the current version; the live site reports it at
https://ballotta.org/version.json. Releases before 1.0.0 were numbered on Oct 17, 2026, from the commit history, one
per milestone; each is tagged `v<version>` at the last commit of that milestone. Issue numbers are GitHub issues;
"audit #N" is a finding in `docs/audits/2026-10-17-cold-audit.md`.

---

## [Unreleased]

_Nothing yet._

## [1.6.0] — 2026-10-31

Come back after Nov 3, and a mailing list for the next election (Lane, Oct 31).

### Added
- "Come back to see how your choices did": a box at the top of the ballot, on the laptop and the phone, until Nov 4
  (Austin time). It shows an example result (a made-up proposition, with made-up numbers) and says to come back on the
  same device or use Keep my picks. Its X, in the corner, hides it on this device for good; Clear everything brings it
  back. From Nov 4 the ballot shows the results instead, and the box is gone. On the phone, moving to another contest
  starts at the contest, just under the box.
- "Your ballot, with the results": How it works, opened from the box. A before-and-after picture of a ballot (made-up
  names and numbers, in the results' own wording), three steps, the way from election night to official, and four
  questions.
- "Ballotta will be back for the next election": the last thing on every page, both layouts, before and after the
  election. Email me before the next election opens Buttondown's sign-up page (buttondown.com/ballotta) in a new tab: a
  link, not a form, so the page still sends nothing and the email address never passes through Ballotta. Neither prints.
- Two new counts, with no details beyond the box's two actions: `come_back` and `mail_list` (README).

### Tests
- Browser: the box on both layouts, its corner X and what it remembers, Election Day and Nov 4, the phone's moves,
  printing, Keep my picks from the box; the mailing list last on every layout and view, its link, its count, and the
  phone's bottom bar never covering it.
- `mutate_results.py`: fourteen new mutants (R137–R150).
- `phone_glance_vote_and_crib_fit_the_screen`: "opens its contest at the top" now means just under the header while
  the box is above the ballot (`contest_at_top`).
- `phone_backup_nudge_after_fifth_pick`: "as far down as it goes" is the end of the ballot, not of the page (the mailing
  list comes after it).

## [1.5.4] — 2026-10-23

Campaign links only (checked from Lane's Mac, Oct 23).

### Changed
- Four candidates' campaign sites moved to new addresses, and Learn more links them there: Candace L. Hunter
  (hunterforaisd.com), Perla Muñoz Hopkins (perlahopkins.com), Serenity Coats (serenity4education.com) and Vikki
  Goodwin (vikkigoodwin.com) (#120).
- `check_sites.py` keeps the printed address for two redirects Lane reviewed: luckfortexashouse.com (it forwards to its
  site builder's address) and SavingManor.org (it forwards to a page that couldn't be confirmed as the candidate's).
  The rule is version 3, so the build takes only results checked with it.

## [1.5.3] — 2026-10-22

Results parsers only; the page itself doesn't change.

### Fixed
- **The state's canvass report of a general election** stopped at its first office: a general election's report
  says "Total Votes", not "Total". And its pages repeat a header and end mid-contest (64 of 86 pages in Nov 2024's),
  so the header would have joined an office's or a candidate's name. The header and the page footer now go by their
  place on the page. The SOS's write-in mark (WRI) no longer sticks to a name (#163).
- **Hays's report** of a general election: its page header names the election differently each year ("Nov 5 2024
  General Election Official"), and a contest that opened a page took that line into its name, which its key would
  then have held. The header now goes by its place (#163).
- **Clarity's partisan names** (Travis and Bastrop): a partisan race prints the party first ("REP Ted Cruz"); it's
  dropped, so a name matches Ballotta's exactly rather than by its words. Travis's county offices on Nov 3 are
  partisan (#163).

### Tests
- Fixtures from the Nov 5, 2024 general election, downloaded by Lane: the state's 86-page canvass report
  (`sos-49664-canvass.pdf`, 592 offices), Hays's official report (`hays-2024-11-official.pdf`, 66 contests) and
  Bastrop's Detail XML (`bastrop-2024-11-detail.zip`, 59 contests; the first Bastrop file read). Results tests 59
  (from 56); back-end mutants B62–B64 and B66–B69.

## [1.5.2] — 2026-10-22

### Fixed
- Pressing Enter twice on an address started two lookups and counted both; the same address, while it's being looked
  up, is now asked once (#127).
- A share name typed all in lowercase with a party glued to its end ("lanegop"), or spelled in boxed or circled
  letters, got past the name check; both are refused, and "Lanegop" is still a name (#127).
- A tampered stored pick under "constructor" or "__proto__" made a Keep link say it was damaged; such keys are dropped
  (#127).
- "Ballotta is back" counts only the page's own answer, not a network sign-in page that redirects the check (#127).
- The backup card's fallback focus on a phone is the paper, not a hidden button (#127).
- The page has one viewport tag, not two (#122).

### Changed
- Opened from the old preview's Home Screen icon, ballotta.org/next/ says: "This icon is for the old preview. To keep
  Ballotta on your Home Screen, delete this icon, open ballotta.org in Safari and add it again." (Lane, Oct 22; #127).
  In a browser it still sends people on at once.
- The share link is prepared once typing in the name box pauses, not on every keystroke; the name's note still
  changes at once (#127).
- Housekeeping (#122, #124, #87): no line carries two pairs of one layer's markers (a pipeline test keeps it so); dead
  phone CSS and stale comments removed. The old hidden page itself stays until after Nov 3 (#86, Lane).
- Docs (#128): the plans and the Oct 17 audit say where their logs and status now live.

### Tests
- New site tests for each #127 item; pipeline tests for one viewport tag and one marker pair per line.
- Mutation runners (#182): 34 anchors brought up to date (24 stale since before 1.5.1, 10 moved by this release), and
  all five runners run whole again: desk 503 of 506 (W6x, W6z and D7 retired as redundant, reasons in the file), phone
  155, streets 23, results 130, back end 61, every one killed. Tests that passed for the wrong reason were tightened:
  a key's own pick announcement (F5), warnings after Change address then Back (F15, F17), the offline copy's decoy
  cache (P76), a town name at the map's edge (X17), share names and sections apart (D68). New desk mutants W19–W29.

## [1.5.1] — 2026-10-22

### Fixed
- Two tabs acting at the same moment: a pick or a reason saved in one tab before the other tab's save had reached it
  wrote over that save. Each save now re-reads what's stored and writes only its own change; every reason box waiting
  to be saved keeps its text, not just the last one typed in (#119).
- On the laptop, Clear my picks left the open reason box, and At a glance, showing the old reasons; one more keystroke
  saved the old reason back (#131).

### Changed
- `check_sites.py` links a campaign site that moved to another name (and answers there) at its new address, without
  the query string; a site that stays on its own name, or a bot wall's challenge page, keeps the address it was given
  (#120). The next run records the new addresses.
- Workflows: Build check and Pages' pipeline job install the PDF libraries pinned by hash (`requirements-results.txt`);
  the release tag job has a timeout; Pages' comments say the branch-publishing case is only a fallback (#121).
- `_site/` is ignored; the requirements say Python 3.10+, as the README does (#121).

### Tests
- The browser runs in Austin's time zone and every clock time a test sets is Austin's, so the suite passes on a
  machine in any zone (#115). A stubbed run that had to ask the live county fails and lists the requests (#116).
- The answer key against the ballot: write-ins where the ballot has them, every English line accounted for, measure
  titles whole; vote sites against the County Clerk's own early-voting and Election Day lists (#118).
- New site tests for #119 and #131; desk mutants W14–W18, with W6b, W6r, W6ac, W6ai and A15 re-anchored.

## [1.5.0] — 2026-10-22

### Added
- **The runoff** (Phase 4, `docs/plans/2026-10-21-the-runoff.md`): while a runoff on your ballot is official and not yet
  held, the menu and the rail get a "Runoff · Sat, Dec 12" group with Decide, Where to vote and Print your choices, a
  ballot of its own under a plum band (the date, days to go, early voting, who can vote). Runoff picks and reasons are
  kept apart from Nov 3's, which never change; the result card's What's next opens it. Where to vote says the county
  hasn't posted runoff vote centers yet, never the Nov 3 list. With several runoffs, Previous and Next (and J, K, N)
  step through them, and the band names each race's own voters and date (W100, W108). On the phone, the main view
  names the runoff, and the bottom bar steps back through its contests to the results.
- "What's a runoff?" in the canvass explainer (W105).
- A runoff with no date yet says so in What's next (W111). After the runoff, its contest links to the county for the
  result, over bars labeled "Nov 3 result" (W113); from the day before, the band and Where to vote send voters to the
  county (W114).

### Changed
- On an unofficial count, a runoff pick line says "so far" (W112) and the summary doesn't count it as "didn't win".
- On the runoff's pages, Clear my picks clears the runoff's picks only (W110); its reason box says "Private · kept on
  this device" (W115); its printout prints "Undecided" for an undecided race (W116); in an iPhone Home Screen app its
  Print note says runoff picks stay in the app (W109).
- The results pipeline (from the deep audit, `docs/audits/2026-10-21-deep/`):
  - Nothing posted before the polls close is a result, and the published file starts empty (#152).
  - One bad file, key or contest holds only itself, listed in the PR as HELD; files the build can't use are set aside
    in `source/results/rejected/`; the kill switch is read first; while paused, what voters saw is kept (#153).
  - An excluded file rolls back quietly; "Corrected" only when the published numbers came from it and now differ, and
    that waits for Lane (#154).
  - Counties with no file (ACC's Caldwell and Lee) count from the canvass record, with its own time (W106); Austin's
    council districts list only the counties with their voters, and ACC's Lee part has its own bound (#155); a
    county's final file is the official numbers (#156); County Clerk's declared write-in (#157).
  - Only Nov 3's files are read; county keys carry the county's name for the contest; `suggest` ranks by title and
    covers the statewide races' Travis breakdown (#158).
  - Workflows: the self-merge merges only the commit it checked; the publish job takes back only results and checks
    the verdicts itself; the build job's packages are pinned by hash; Pages takes one page from the demo's branch (#159).
  - One PR stays (Lane): it says when new numbers wait behind a verdict change (#160).
  - Fetching retries, never fails the run, reports each source in the PR, and checks the SOS feed's time zone and
    election date (#161).
  - Hand edits to the map are kept; the runbook matches the code; the schedule runs to Dec 20 (#162).
  - Parsers: Hays's report with any number of vote types; empty Williamson contests refused; the state's canvass report
    is its own source (W107); the SOS's Green party codes (#163).

### Fixed
- A page left open past midnight redraws what's dated (#164).
- The runoff's pages: picks across two tabs (#165); several runoffs (#166); printing, Ctrl+P included (#168); a tie that
  went to a runoff after its day (#169); the phone (#171); focus, names and announcements (#172); layout at 1024px and
  a gap under the band (#173); the runoff's views in the counts (#174); a saved runoff view after a rollback (#176).
- Small fixes (#177): the caret on new results; the timeline in date order; All Travis County results no longer uses up
  "Since you last looked"; a past canvass date isn't said as if to come; a friend's initials leave the rail after the
  election; result lines in the rail wrap; even lines around a link on the phone.

### Tests
- Results: 56 tests (from 44), with fixtures from the Nov 2025 special's SOS feed and canvass report. Back-end mutants
  B33–B61: all 61 killed. Site: 200 tests (from 184). Page mutants R114–R136: all 130 killed (R63 and R119 retired
  as equivalent, with the reasons in the file). `mutate_backend` takes the clone's mutation lock.

## [1.4.0] — 2026-10-21

### Added
- **After the election, your ballot becomes a record of how it did** (`docs/plans/2026-10-21-after-the-election.md`,
  the design Lane approved Oct 20–21). Nothing changes before Nov 4: from Nov 4 (Austin time), once `results.json`
  has results, the page turns to results:
  - The menu is Results · At a glance · All Travis County results · Print your results.
  - Each contest's paper is its result: whether it's official, the verdict, neutral bars, How Travis County voted, your
    pick and your reason with it, "Your choice" as you marked it (read-only), and what you read before voting, folded.
  - A band at the top: "Your ballot" (official so far), "Your N picks" (won or leading, didn't win or behind, too close
    or not settled), "What's next", "Since you last looked", and "Where things stand", from election night to the
    Legislature.
  - The rail says "N of M official" and each contest's result in a few words, with Too close and My picks filters.
  - At a glance is Contest · Result · Your pick · Your reason, with "Only contests I picked in".
  - Print your results puts each contest's result beside your pick.
  - All Travis County results is its own page, with the levels as its list, search and filters. It needs no address
    (from the landing page's "or see all Travis County results", or ballotta.org/results/).
  - The phone: the same, with the summary at the top of the list and What's next when a runoff is coming.
  - New results arriving while you read keep your place, what you opened and your focus, and are announced politely.
  - "No call yet" when the numbers are in but the result is decided at the canvass (W69).
  - The words are the approved wording cells W1–W97, `docs/plans/2026-10-20-results-wording.md`.
- **A locked demo at ballotta.org/demo/**, for trying the results pages with made-up names and results: three scenes
  (Nov 4, Nov 13, Dec 8), password-locked (AES-GCM; the password is a GitHub secret), kept out of search, its own
  storage. Built by the Pages workflow from `source/build_demo.py` and `source/demo_lock.mjs`.

### Fixed
- A several-seat race's winners are "elected" (the results rules said "won"); one bad county file no longer stops the
  results run; and the page refuses any results entry the drawing code can't show (the cold audit, #134–#150,
  `docs/audits/2026-10-21-results-cold-audit.md`).

### Tests
- The results tests follow the after-election layout; every state on the canvas's Pieces board is checked through At
  a glance and the printout; the demo is checked in a browser; 97 results mutants, all killed. Before Nov 4 the page
  reads and looks the same as 1.3.1 in every view, laptop and phone (compared word for word and pixel for pixel).

## [1.3.1] — 2026-10-20

### Fixed
- **Numbers in Zilla Slab sit level.** The headline font defaults to old-style figures, where 3, 4, 5, 7 and 9 drop
  below the line and 6 and 8 rise above it, so a count like "5" looked lower than the "6" beside it. Every number on the
  page now uses the font's lining figures, all one height on the baseline (Lane, Oct 20). Public Sans already drew
  lining figures, so body text doesn't change.

## [1.3.0] — 2026-10-19

### Added
- **The street map is live** on ballotta.org (Lane, after trying the preview): Where to vote's map draws freeways,
  highways, major streets, the lakes and the river under the vote-center dots, with labels on the main highways,
  instead of a grid, and a town name a vote center would cover moves just above or below it (or is left out when
  neither is clear). Drawn on your device from
  street data built into the page (U.S. Census Bureau TIGER/Line, 2024, public domain): no map company is asked
  anything, and it works offline. Credited under About this test. Previewed at next/ in 1.2.1.

### Changed
- **ballotta.org/next/ sends people on again**, to ballotta.org with any picks link, and its offline copy removes
  itself, as after the phone layout's promotion (`STREETS_LIVE = True`). The main page's offline copy keeps `next/`
  from its first install again.

## [1.2.1] — 2026-10-19

### Added
- **A street map, in preview at ballotta.org/next/** (Lane, Oct 19). Where to vote's map draws freeways, highways,
  major streets, the lakes and the river under the vote-center dots, with small labels on the main highways and roads (I-35,
  MoPac, 183…), in place of the graph-paper grid. It is drawn on your device from street data built into the page
  (U.S. Census Bureau TIGER/Line, 2024, public domain, simplified by `source/fetch_streets.py`), so no map company is
  asked anything and it works offline: the caption's promise stands as written. A town name a vote center would cover
  moves just above or below it. Only the preview has it until Lane approves it there (`STREETS_LIVE = False`):
  ballotta.org itself is unchanged.

### Changed
- **ballotta.org/next/ is a preview again**, of the street map: the main page with it on, its own offline copy, a
  "[Preview]" title, nothing counted, and a `noindex` so search engines list only ballotta.org. A Home Screen app added
  from the Oct 15–17 preview opens it again instead of being sent on; after promotion it is sent on again. While
  `next/` is a preview, the main page's offline copy no longer fetches it at install (a 600 KB page most phones would
  never open), and a phone that kept the old hand-off page drops it, so the preview is never shown as the old page
  (a Home Screen app from the old preview then opens `next/` offline only after one online visit; a phone that
  installed the old preview and hasn't opened Ballotta since fetches the preview once when it next opens ballotta.org,
  since the main page's request to update `next/sw.js` now reaches the preview's own copy); promotion puts all that back. Mutant W3f re-anchored to hold either way.

### Tests
- `street_map_waits_for_promotion` and `street_map_draws_streets_and_asks_nobody` (the second runs where the page has
  the street map: `BALLOTTA_PAGE=next/index.html` until promotion), and `street_data_is_whole_and_in_view` in the
  pipeline tests; `tests/mutate_streets.py`, 28 mutants. The two promotion tests set `STREETS_LIVE` as well as
  `PHONE_LIVE`, since next/ sends people on only once nothing is in preview.

## [1.2.0] — 2026-10-18

### Added
- **A share link has its own card** (Lane, Oct 18). Pasted into Messages, WhatsApp or anywhere else, a Share my picks
  link showed the generic Ballotta card. It now goes to `ballotta.org/picks/`, whose preview says "Here's how I'm
  voting": "My Travis County picks for Nov 3. Open to see them next to your own ballot.", with a ballot slip in place of
  the dots, titled "My picks for Nov 3 · Ballotta" (option B, Lane's choice). That page hands the picks straight on to
  Ballotta, replacing its own history entry, and counts nothing. The card is the same for everyone: the picks and the
  name still travel only after the `#`, which no server sees. The offline copy keeps `picks/` from the start, so a share
  link opens on a phone with no signal as before. Share links made before still open; Keep links and the site keep the
  generic card.

### Tests
- `a_share_link_has_its_own_card`, `a_share_link_opens_from_the_offline_copy`; `link_preview_card_is_drawn_from_its_source` covers both cards;
  `the_site_folder_is_the_whole_site` asks for `picks/` and `og-picks.png`.
- Mutants W3a, W3b and W3d–W3g (W3c, the hand-off with `location.assign`, is equivalent in Chromium, which
  replaces a page that moves on while loading); D57 re-anchored.
- Remediation audit: Pass 1 (picks/ kept offline from the start; the share page names its own address, `og:url`,
  instead of pointing at the site, which some unfurlers follow to the generic card).

## [1.1.7] — 2026-10-18

**The small bugs filed so far** (round-2 wave 2's voter-facing items, brought forward), and the bump check.

### Fixed
- **Add to Home Screen's "Copy my picks link" always copies a link the Home Screen app can open** (#129): picks and
  reasons, whatever the Keep sheet was last set to; when long reasons make that link too long to open, the picks only,
  saying "✓ Copied (picks only: your reasons made the link too long)" (Lane's words).
- **Next no longer ping-pongs** (#125): moving on with Next from the only contest left undecided leaves it; Next keeps
  going in order, to At a glance (laptop) or the crib sheet (phone), instead of pointing back at it. From At a glance
  or the crib sheet, Next undecided names it again.
- **A long reason is cut in the crib sheet and At a glance** (#126; Lane): its first 600 characters, then "…". The box
  keeps every word.
- **Clear my picks, and loading a Keep link, drop a reason still waiting to be saved** (#110), so another tab's save
  can't bring it back.
- **The saved-copy bar asks whether Ballotta is back a second after load** (#114), not first after 20 seconds.
- **A new share name hides the link just shared** (#98).
- **Hiding a friend's picks keeps a Keep link left waiting** (#130).

### Added
- **The bump check** (#117, `source/check_bumped.py`): a push that changes what the site publishes without a new
  `VERSION`, or whose VERSION is lower than a release already tagged (a bare `git revert` of a release), is refused,
  by the Pages workflow's deploy job before it deploys (even when the pipeline tests are skipped) and by Release check. Since 1.1.6 a page left open
  learns of a newer release only from a higher version.

### Tests
- `copy_my_picks_link_for_the_home_screen_always_opens_there`, `next_keeps_going_past_a_contest_left_undecided`,
  `a_long_reason_is_cut_in_the_printout_and_the_glance_table`, `clearing_picks_drops_a_reason_waiting_to_be_saved`,
  `a_new_share_name_hides_the_link_just_shared`, `hiding_a_friends_picks_keeps_a_waiting_keep_link`;
  `phone_saved_copy_bar_follows_the_site` waits 6 s for the first answer, not a visibility change. Pipeline:
  `a_change_to_the_published_site_needs_a_new_version`.
- Mutants W2a–W2j, W2l–W2n and P158–P164; M29, C5, P122, P130 and P159 re-anchored.
- Remediation audit: Pass 1 (Next's "left" contest is now forgotten on any other move, a new ballot or Clear my picks;
  the bump check also refuses a VERSION lower than a tagged release and a clone without history or tags, and runs in the
  deploy job; a picks-only link shown to copy by hand says so; #131 filed).

## [1.1.6] — 2026-10-18

**Round-2 cold audit, wave 1** (early voting, week 1): what a voter could lose or be misled by.

### Added
- **A page left open learns of a newer release** (round-2 #7, #105). A Home Screen app resumed, or a tab left open,
  never reloads by itself, so it kept the page it opened with. When it comes back into view, and every 10 minutes while
  in view, never more often, it asks for `version.json` past every cache; a newer release brings the bar "A newer
  Ballotta is available." with Reload (Lane's words). It never reloads by itself, and an older copy kept offline says
  nothing. This is what carries every later fix to phones already in use.
- **Paste my picks link in an iPad's Home Screen app held sideways** (round-2 #14, #112): the laptop layout's menu had
  no way to bring picks in from Safari.

### Fixed
- **An unknown precinct no longer drops US Rep, State Senator and State Rep** (round-2 #8, #106). For a precinct the
  Legislative Council table doesn't list (one the county adds or renumbers, or none), they come from the county's own
  district fields, marked Double-check: "Matched from the county’s district record for your address; your precinct is
  new to us. Check your official ballot." (Lane's words), after a reload too.
- **County Judge comes before the County Courts at Law**, as on the ballot (round-2 #26, #123). Moved in the list
  only: contest ids, and so every Keep and Share link, are unchanged.
- **A refused share name leaves the name kept from before alone** (round-2 #9, #107); a box emptied on purpose still
  clears it.
- **A stray tap outside "Load your saved picks?", or Escape, keeps the link** (round-2 #10, #108; Lane): only "Load my
  picks" and "Not now" answer it, and a reload asks again.
- **A Keep link too long for this page to open can't be sent or copied from Keep my picks** (round-2 #11, #109) until
  the reasons are left out; focus then moves to the send button once it can be used. (The Add to Home Screen steps' own
  "Copy my picks link" doesn't check yet: #129.)
- **Framed, or with its first script stopped, the page says "Open ballotta.org directly."** (round-2 #13, #111; Lane's
  words), a link, instead of showing a blank page. With JavaScript off it still shows only the JavaScript note.
- **A second Keep link while "Load your saved picks?" is open isn't called damaged** on older browsers (Chrome < 114,
  Safari < 17) (round-2 #15, #113).

### Tests
- `a_page_left_open_learns_of_a_newer_release`, `an_unknown_precinct_still_gets_its_federal_and_state_contests`,
  `a_stray_tap_keeps_the_keep_link`, `a_second_keep_link_while_asked_is_not_called_damaged`,
  `an_ipad_home_screen_app_held_sideways_can_paste_picks`; `a_refused_share_name_is_said_to_the_sender`,
  `a_keep_link_too_long_for_chat_apps_can_leave_the_reasons_out` and `page_refuses_to_show_in_another_sites_frame`
  extended. Pipeline: `contests_within_a_level_are_in_ballot_order` (for every candidate contest whose title is a line
  of the ballot).
- Mutants W1a–W1s (laptop runner) and P146–P157 with P150b (phone runner); H10, Y4, P89 and P114 re-anchored.
- Remediation audit: Pass 1 (focus lost after "Leave my reasons out"; #129 and #130 filed), Pass 2 (an overtaken
  Keep pack could move focus into a reopened sheet; it now touches nothing).

## [1.1.5] — 2026-10-18

**Round-2 cold audit, wave 0** (`docs/audits/2026-10-18-cold-audit.md`, "round-2 #N"): what had to be right before
the site goes public on Oct 19.

### Fixed
- **Travis County MUD No. 41 goes back to no address** (round-2 #1, #99). 0.6.3 sent its seven contests (five tax and
  bond measures) to the 1,217 addresses the county codes `M41`. The county's codes run in sequence, not by district
  number: the districts created in 2026 sit at M118–M128, MUD No. 41 was created in May on land whose water system is
  yet to be built, and M41 sits among long-established districts. So M41 is very likely another district, and those
  voters were shown contests not on their ballot. Until the Tax Office names its code (#56), no address gets MUD No. 41,
  and the page says again that one district can't be placed on a map yet. A ballot saved, or a link made, while 1.1.4
  showed it no longer lists it. The build now stops when a district holding its confirmation election (so, a new one)
  reaches more than 300 addresses.
- **Print in an iPhone or iPad Home Screen app says how** (round-2 #6, #104). Printing does nothing there (Lane tried
  it on his iPhone; Safari prints). There the note under the Print button says: "Printing doesn’t work in a Home
  Screen app. To print, tap Keep my picks, then Copy link, and open the link in Safari. Print from there." (Lane's
  wording), and a tap on Print turns the note into a warning instead of doing nothing.
- **The campaign-site check was run again** (round-2 #2, #100), from an ordinary connection, under 1.1.3's rule: no
  link a voter sees changes (Okey Anyiam's site answers; Lane checked it in a browser too, and the two 404s stay
  unlinked).

### Changed
- **Search engines may list ballotta.org** (round-2 #6, #104; Lane): the page no longer carries `noindex`. The old
  preview address, `next/`, keeps it.
- **Pages runs the pipeline tests before it deploys** (round-2 #3, #101), so a data edit the build faithfully copies
  can't go live before the checks say so. They run in their own job, without the deploy's permissions; a deploy by
  hand can skip them if PyPI is down during a rollback (`docs/RUNBOOK.md`).
- **The workflows run on Ubuntu 24.04** (round-2 #4, #102), not `ubuntu-latest`, which moves to Ubuntu 26 from Oct 19.
- **`check_sites.py` records the rule it used and the sites it checked, with their results**
  (`data/sites_checked.json`), and `build_learn.py` stops when any has changed since (round-2 #2); a run behind a proxy
  records no stamp.

### Added
- **`docs/RUNBOOK.md`** (round-2 #5, #103): taking back a bad release, step by step, as a forward release.

### Tests
- `mud_41_reaches_no_address_until_its_code_is_confirmed` replaces `mud_41_reaches_its_addresses_marked_double_check`;
  `a_restored_ballot_keeps_each_contests_own_caveat` uses Travis County MMD No. 1 as its contest whose whole rule is
  uncertain; `phone_print_in_a_home_screen_app_says_how`.
- Pipeline: `rules_are_rebuilt_and_new_districts_stay_small`, `campaign_sites_were_checked_with_todays_rule`,
  `search_engines_may_list_the_page`.
- Mutants D60, D61 and D61a retargeted to the unrouted contest; P137–P145 for Print in a Home Screen app (on screen,
  said to a screen reader, on every tap).

## [1.1.4] — 2026-10-18

**Wave 6, the voter-facing part** (cold audit). #86–#90 (refactors, and removing the phone rollback) moved to after
the election (Lane).

### Fixed
- **Two tabs stay in step** (#92): a tab takes the other tab's saved picks and reasons and shows them, so the one that
  saves last no longer writes over the other's changes without a word, whichever view it shows. A reason being typed
  when the other tab saves is kept.
- **A share name the friend's page would refuse is said to the sender** (#93): "That name can’t be used. Try your first
  name." (Lane's words) appears under the name box once typing pauses (so "Dem…" on the way to "Demi" isn't refused),
  and the name is neither sent nor kept. Names are cut at 30 characters, never inside one. Latin letters with a stroke,
  hook or bar ("GØP", "Đemocrat", "GƟP", "ᴃallotta": 250 letters, from Unicode's own names) are read as their base
  letter as well as the way Unicode's look-alike table reads them, and shouted party names glued on ("LANEGOP") are
  refused like the others; "Łukasz", "Søren", "Đặng", "GOPAL" and "ERDEM" are fine.

### Changed
- **Reasons are saved when typing pauses** (#91): a reason is kept in memory at every keystroke but saved, and the rail
  and crib sheet redrawn, 150 ms after the last one (each save reached every other tab), and at once when the page is
  hidden, closed or printed. Clear everything drops a reason still waiting to be saved, in either tab.

### Tests
- `a_reload_before_answering_keeps_the_keep_link` waits for "No" to land before reloading (it failed once under load).

## [1.1.3] — 2026-10-18

**Process** (cold audit wave 5), and three vote center spellings.

### Fixed
- **Three vote centers spelled as the county spells them elsewhere** (#85, approved by Lane): Millennium Youth
  Entertainment Complex's "East Media and Conference Room" and Gus Garcia Recreation Center's "1201 E Rundberg Ln" in
  the early voting list, and Hartfield Performing Arts Center's "5800 McNeil Dr" in the Election Day list. All 45 early
  voting sites now read exactly as their Election Day entries.

### Added
- **A check on every push** (#81): the Build check workflow runs `build_site.py --check` (rebuilds in memory, writes
  nothing, fails if a committed file isn't what the build writes, which catches a hand edit or a left-behind mutant, or
  if a rollback build's markers don't pair up) and the pipeline tests. No browser, no county server.
- **`requirements.txt`** (#82): every Python package the build and tests use, pinned, with one install line in the README.
- **Only the site is published** (#83): the Pages workflow deploys a folder holding the built pages and the files they
  point at (`build_site.py --site`; a phone rollback keeps next/ in it), so tests, docs and sources are no longer
  served. (The Pages setting moved to GitHub Actions the same day; the live site confirms it.)
- **`SECURITY.md` and `fonts/OFL.txt`** (#84): how to report a problem privately, and the fonts' license with their
  copyright notices. The code stays all rights reserved (README).
- **Sources for two inputs** (#85): `source/fetch_combos.py` records the county query behind the district-code
  combinations (renamed `source/data/district_combos.json` and refreshed; the routing it checks is unchanged), and
  `source/og.html` draws the link-preview card (`make_icons.py --og`; `og.png` is redrawn from it, the same to the eye,
  and carries the hash of what it was drawn from, so a test can tell when it's out of date).
- **The county's answers, recorded** (#78): `BALLOTTA_STUB_COUNTY=1` answers the tests' county lookups from
  `tests/county_answers.json`, so the suite runs when the county's server is down or slow; the mutation runners use it
  by default. `county_is_live` always asks the real server and fails if its answers have changed.
  `BALLOTTA_RECORD_COUNTY=1` records them again.

### Changed
- **The mutation runners run alone** (#79): a run holds `.mutate-lock` and refuses to start while another run's lock, or
  a half-written `*.mutate-tmp`, is there; a run killed outright leaves the lock, since a mutant may still be on disk;
  the build refuses to run while the lock is there.
- **Every test a mutant names must be able to see it** (#80): a template or build-script mutant only reaches tests that
  run the build; a built-page mutant only tests that load the page or read it. Three lists named a test that couldn't
  (L9, G3, H13), and lose it.
- **The pipeline's loose ends** (#85): `check_sites.py` counts a site as broken when its name doesn't resolve, its
  secure connection fails or its certificate is refused (an incomplete chain, which browsers complete, is not), even
  when an http redirect answered first, and a break only if it repeats, with `build_learn.py` using the same rule; a
  site that answered over https keeps its https link, and the check stops behind a proxy, whose own failures look like
  broken sites; `parse_lwv.py` compares guide sites whole (one Facebook page no longer vouches for every other) and
  leaves out the guide's Williamson County measures, which `build_learn.py` now refuses to carry unread; the design
  checker's file-wide waiver records why it can't be narrower.
- **No hash pin on the live page** (#77): `LIVE_SHA` was re-pinned in every commit that changed the page, so it guarded
  nothing the build-equals-disk check doesn't.
- **The ballot pipeline says what can't be rerun** (#55): `parsed.json` is a frozen snapshot of the Sep 30 PDF (its
  hand-made column extraction was never committed); the tests against the corrected PDF are its check. Building the key
  straight from the PDF is #97, after the election.

## [1.1.2] — 2026-10-18

**Phone layout follow-ups** (cold audit wave 4).

### Fixed
- **On the laptop, "Next" never points at the contest already open** (#53). When it's the only undecided one, Next goes
  on in ballot order ("Next: …"), and from the last contest to At a glance ("Last contest · see At a glance").
- **A server error no longer beats the copy saved on a phone** (#74): a 5xx, 408 or 429 that arrives within 4 seconds (a
  deploy, a proxy, a rate limit) opens the kept page with the bar "Ballotta isn’t answering, so this is the copy saved on your phone." A 404
  is shown as it is, so a page that's really gone is never masked by its copy.
- **The saved-copy bar says when the site is back** (#73): once the site answers again, it reads "Ballotta is back."
  with Reload (Lane), where before it stayed until Try again on a slow line and vanished on "online" even when the site
  didn't answer. The page checks when it comes back into view, when the phone says it's online, and every 20 seconds;
  only an answer quick enough that Reload would really get the newer page counts, and if the site stops answering
  again the bar says so again.
- **The offline copy marks its page by the page's own opening tag**, whatever attributes it carries, so a template
  change can't quietly hide the saved-copy bar (#75); `/` and `/index.html` are one kept copy (#76).
- **The map shows all five closest vote centers from an outlying address** (#76): from Manor, Webberville, Lago Vista
  or Mustang Ridge, four or five of them were off the map. It widens just enough; closer in it is unchanged. Town names
  stay clear of the edges, and center 1 is drawn on top.
- **Phones: "Campaign site" and "League guide answers" are full-size (44px) tap targets** (#51).
- Smaller (#76): the map fold stays open when the vote view redraws; after an Android install, the tab stops offering
  "Add to your Home Screen"; a measure with nothing behind its fold shows no fold; a tablet that loads in landscape
  gets the offline copy once it's turned upright; Next from another view counts as opening a contest, as Back does;
  a share link with no readable picks isn't counted as opened; an open comparison follows a new friend's link; only
  contests and choices on today's ballot count as picks (filtered as they're read: what's stored is never trimmed, so
  an older copy of the page can't delete picks it doesn't know).

### Security
- **The page may now ask its own site** (`connect-src 'self'`), for the saved-copy bar's check: a `HEAD` request, which
  the offline copy never answers.

### Tests
- The share-name mutants are settled (#94): "X-GOP", "J/RNC" and "GOP_X" are now tested (blocked only by one line);
  R19 targets a test with a 9 in it; R8 is equivalent (6,916 generated names) and retired with its reason. #52 was
  already fixed and tested in 1.1.0.
- 19 older mutants whose lines waves 2–4 rewrote are re-anchored to the same behavior (a full mutation run would have
  stopped at the first); the Census check's test now also sends a sandboxed answer from the wrong window. P91 and P115
  are retired: the bar no longer goes on its own.
- The offline copy's install guards are tested (#54): a redirected page and a download cut off midway are never kept;
  the test server learns 301s and stalls.
- Three remediation-audit passes, converged; the first two found two real bugs this wave had introduced (a 404 masked by
  the saved copy; picks deleted by an older copy of the page) and one loop ("back" when Reload would still get the copy).

## [1.1.1] — 2026-10-17

**The privacy promise, verified** (cold audit wave 3).

### Security
- **The counting firewall passes no free text** (#50, #67): a page view's title is the page's own title as it loaded,
  no tag is sent, and the page address goes out in its normal form, this site's `/` or `/index.html` only; a payload
  for any other address is dropped whole (so a future `history.pushState` can't carry anything out). The hostname,
  website id, screen size and language pass only as their true values.
- **The tracker is pinned by its hash** (#68): the build refuses any `umami.js` but the reviewed copy, and the tag's
  `integrity=` makes browsers refuse one too.
- **Framed by another site, the page shows nothing of itself** (#69), even in a frame with scripts turned off (which
  shows only the JavaScript note below). GitHub Pages can't send the header that forbids framing, so the page starts
  hidden and its first script shows it only when it isn't framed.
- **Smaller locks** (#85): the Census answer is taken only from the sandboxed frame's own (`null`) origin; the page's
  data is written so that no text in it can end its script or change how it is read; the build stops on a campaign
  site or source link that isn't http(s); counting happens only on ballotta.org (the lanebecker.github.io entry was
  dead: that address redirects).

### Changed
- **With JavaScript off, the page says so:** "Ballotta needs JavaScript to look up your ballot. Turn it on for
  ballotta.org, or use the Travis County Voter Lookup." (with the county's link), instead of a lookup form that couldn't
  work (Lane's wording).

### Tests
- The mutation runner re-hashes a mutated page's Content-Security-Policy, so a kill means a test noticed the change and
  not that the browser refused the page, and it counts a timeout only if it happens twice (#70, #71); it re-hashes only
  the page itself (census.html and next/index.html keep their own policies). Rerun with it, 21 of the 22 mutants it had
  judged are killed; P93 is equivalent and retired with its reason.
- New mutants over the firewall, the pin, the frame guard and the JavaScript note, link handling, ballot routing,
  `esc()` and both CSPs, all killed (#72). New checks: framed with and without scripts (nothing of the page visible,
  text or not), JavaScript off (only the note), and the guard can never stop the first script's link scrub.
- The test stand-in for the tracker loads before the page (the real tag's `integrity=` refuses a substitute).

## [1.1.0] — 2026-10-17

**Look-ups and dates** (cold audit wave 2), two days before early voting starts.

### Fixed
- **Street names that start like a unit are looked up whole** ("2505 Steck Ave", "555 Unity Dr", "Stevens Rd", "Steiner
  Ranch Blvd" were asked as just the number, so an exact match fell back to "nearby") (#57).
- **Two lookups at once no longer race:** the newer address's ballot stands, whatever order the county answers in, and
  a superseded lookup stops asking (#58).
- **A Census outage is no longer reported as a wrong address:** the page says it couldn't reach the U.S. Census address
  finder, and counts it as `census_unreachable` (#59).
- **Dates follow Austin's clock**, not the visitor's: early voting, Election Day lists and the wait-times note change
  on Travis County's dates wherever the phone is (#61).
- **A ballot reopened from this device or a Keep link keeps each "Double-check" contest's own reason** (the county code,
  the district line), as the first lookup showed (#62).
- **A precinct or map point from a link or storage is checked:** only a precinct number shows, and only a point in
  Texas is used for distances (#63).
- **Reloading before answering "Load your saved picks?" asks again** instead of dropping the link (#66).

### Added
- **From Oct 31 to Nov 2 the wait-times note says the county's Election Day map fills in on Nov 3** (#60).
- **A Keep link too long for chat apps says so**, with "Leave my reasons out": long reasons in Chinese, Japanese,
  Korean or emoji can make a link of 100 KB or more (#65).

### Tests
- `BALLOTTA_TODAY` runs the whole suite as of another moment; as of Nov 1 one test failed and is fixed (#64). A stand-in
  for the county's map server (`stub_county`) lets lookup tests run without it.

## [1.0.0] — 2026-10-17

**Phones get the new layout.** The phone layout that was previewed at ballotta.org/next/ is now the main page, for
everyone, two days before early voting starts. 1.0.0 marks that milestone; it is not a breaking change: every Keep
and Share link people already have still opens.

### Added
- **The phone layout on ballotta.org.** Narrower than 1024px, the page is the laptop's app folded up for a phone: a
  plum top bar ("Your ballot", with how many contests are decided, opens the whole ballot as a sheet; Feedback & Info;
  Share), one contest at a time on the paper with its notes behind a "Learn more" fold, and a bottom bar with
  "← Previous" and "Next undecided →".
- **Add to Home Screen.** Android shows the browser's own prompt; on an iPhone, steps that name and draw Safari's own
  buttons, a private picks link to carry your picks into the Home Screen app, and "Paste my picks link" there.
- **An offline copy for phones and tablets.** The page keeps a copy of itself and opens it when there's no
  connection (or the network takes more than 4 seconds), with a bar that says so and "Try again". It keeps the page
  from its first install, so it opens offline before a second visit; that first download gives up after 8 seconds on
  a slow line. Laptops never get it, and turning the phone layout off again removes it from phones.
- **Versioning.** `VERSION`, this changelog, `version.json` on the live site, release tags, and a check that keeps
  them in step (`source/check_release.py`, run by the build, the tests and a GitHub workflow).

### Changed
- **ballotta.org/next/ now sends people to the main page**, with any Keep or Share link made on the preview, and
  removes the preview's offline copy from phones that installed it (audit #21). The main page asks for that removal
  too, for a phone that only ever opens ballotta.org now; a failed request removes nothing. Anyone who added the
  preview to their Home Screen should add ballotta.org again.
- **A friend's picks are counted when they first appear beside your ballot at any width** (`share_compare`), not on a
  Compare tap, which the phone layout doesn't have.
- **Crib sheet print options survive a window narrowed below 1024px**, since a phone now shows them too.

### Removed
- **The old phone page** (every contest on one long page, with its Compare button).

### Fixed
- **The shared link stays on screen after "Share link".** Since Oct 14 the link just copied vanished at once, and
  where copying fails, so did the selected link you were meant to copy by hand.

### Known issues
- The "Slow connection" bar doesn't clear on its own (issue #73), and a server error that arrives within 4 seconds is
  shown instead of the kept copy (issue #74).

### Tests
- The 31 tests that only ran on the old phone page are retired; 34 ports run on the live page (audit #29). The 117
  laptop mutants that named those tests now name the ports, six are re-anchored on the laptop's own copy of their
  line, and five that promotion made unreachable or redundant are retired.

## [0.6.3] — 2026-10-17

### Changed
- **Travis County MUD No. 41 reaches its voters.** Its 7 contests go to the addresses the county codes `M41`
  (precinct 142), marked "Double-check" until the Tax Office confirms the code (Lane's call; issue #56).
- **"The county's wait-times map fills in once voting starts Oct 19"** now shows on the laptop's Where to vote view,
  as the old phone page always said.

## [0.6.2] — 2026-10-17

**What's on the ballot is the ballot** (cold audit wave 1).

### Fixed
- **Ten "vote for up to N" contests list their candidates in the ballot's order** (MUDs, an MMD, two WCIDs and a
  library district: c154, c168, c176, c179, c192, c199, c202, c203, c204, c214; audit #1). Keep and Share links still
  count those ten in the old order, so every link, old or new, means the same candidates to every version of the page.
- **37 measures no longer end in a stray Spanish caption** ("… Distrito de Austin Community"); every measure's text
  is now read straight from the county's corrected ballot PDF, English only (audit #2).

### Changed
- **The answer key rebuilds byte for byte from `source/ballot/build_answer_key.py`**, with the Oct 14 corrections in
  the script instead of hand-edited into the JSON (audit #3), and records the ballot PDF by its sha256.
- **The build stops** on a contest no address reaches (unless explained), an address with the wrong number of
  representatives, or a precinct missing from the Legislative Council table (audit #4); dropped ballot lines are
  printed, not silent (audit #5).

### Tests
- `tests/test_pipeline.py`: the key against the PDF (choice order, measure texts, line by line; party labels; the
  count of measures).

### Known issue
- For about seven minutes on Oct 17, between 663feec (every link in the new order) and 1789fae (the old order kept for
  links), the live page made Keep and Share links that list those ten contests' picks in the new order; every later
  page reads them in the old one, so such a link can show the wrong candidate in those ten. Few if any exist (#127).

## [0.6.1] — 2026-10-17

### Changed
- **Laptop: At a glance's pick column fits every name on the ballot**, and its title matches the other views' size.
- **The "Crib sheet" tab is "Print your choices"**; its page is titled "Crib sheet", and the printout is headed "My
  ballot choices".
- **Every view's title sits the same distance below its small line**, as Decide's does.

## [0.6.0] — 2026-10-16

### Added
- **A preview of the phone layout at ballotta.org/next/** (ballotta.org itself unchanged): the laptop app folded up
  for a phone, Add to Home Screen and an offline copy with a kill switch; Home Screen steps that name Safari's own
  buttons, and a bar that says when you're looking at the saved copy; "Your ballot" as the top bar's title, with
  "← Previous" and "Next undecided →" at the bottom.

## [0.5.0] — 2026-10-15

### Security
- **The page is locked down** (#36): a Content-Security-Policy built from the hashes of the page's own scripts, no
  referrer to any site, and the Census geocoder in a sandboxed frame (`census.html`) that hands back only a point.

### Added
- **A one-time card after the 5th pick (and at 25) suggests a backup link** (#48), and at the first pick the page asks
  the browser to keep its data (#49).
- **"Clear everything on this device" in the phone page's footer** whenever anything is stored (#42).
- **The laptop's "Print…" opens the Crib sheet view.**

### Fixed
- Saved picks, reasons, share names and generations are checked when read, so junk can't break Keep or Share
  (#20, #44); share names fold look-alike letters and party nicknames (#21, #43); a pick past "vote for up to N" is
  refused with a note that says why (#33); a tab left open past midnight moves to the new day (#34, #47); laptop moves
  and announcements are spoken in order, none cut off (#39, #45); a new ballot clears an older link's notice (#40);
  and smaller fixes (#22–#24, #32, #46).

## [0.4.0] — 2026-10-15

### Added
- **"Clear everything on this device"** next to Clear my picks (and in the laptop menu) removes every Ballotta key
  and reloads other open tabs (#29).

### Changed
- **Usage counts grow to 25 named events behind an allow-list firewall that fails closed**: no address, no picks, no
  candidate names, no query strings or #links. Page speed is counted too, as bare numbers only. Do Not Track and
  Global Privacy Control now turn counting off entirely, page views included.

### Fixed
- A lookup no longer hangs when the county server fails after the Census fallback.

## [0.3.0] — 2026-10-15

### Added
- **The laptop layout** (screens 1024px and wider): a plum column with your ballot's outline, search and filters; one
  contest at a time on a paper with notes beside it; keyboard shortcuts; At a glance; a map of vote centers drawn on
  the page; a crib sheet preview; Feedback & Info. A plum landing band with a gold "Travis County only" strip, the
  tagline "Don't wait to meet your ballot in the booth." and a FAQ. Phones unchanged.

## [0.2.1] — 2026-10-14

### Changed
- **The site moves to ballotta.org** (the old lanebecker.github.io address redirects there). Picks saved in a browser
  at the old address stay there; a Keep link carries them over.
- **Keep and Share links are short and safe to paste into chat apps** (`#k2…`/`#s2…`, about half as long; Messages
  was cutting the old ones); older links still open (#19).

## [0.2.0] — 2026-10-14

### Added
- **Learn more on every race:** an office note, and each candidate's campaign site and League of Women Voters guide
  answers, shown the same way for everyone and saying so when something is missing. Measures: the ballot text; Austin
  Props A–B in plain words, the money split and the City's tax estimate.
- **Where and when to vote:** 45 early and 201 Election Day vote centers, by distance, with late hours, bus routes,
  wait times and ID rules.
- **Keep my picks** (a private link to yourself) and **Share my picks** (a link for a friend, with what to include),
  a friend view and compare.
- Anonymous counts of a few actions (Umami); the About box points at the county's Voter Lookup.

### Changed
- **The ballot follows the county's corrected consolidated ballot** (corrected Oct 14).

## [0.1.0] — 2026-10-13

### Added
- **Ballotta's first test:** look up a Travis County address against the county's own voter-district data, see your
  Nov 3, 2026 ballot, make private picks with reasons, and print a crib sheet. Zilla Slab and Public Sans, self-hosted.
