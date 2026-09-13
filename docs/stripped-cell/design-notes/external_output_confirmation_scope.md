# External output confirmation via `io_name` + real file writing — scoping note, queued (Alan/Claude, 2026-09-08)

## Real status: queued, not scoped in detail, review when we reach it

Raised while discussing the LaTeX-input path and the broader TRIX
family's own eventual need for real output, not as an immediate task.
Alan's own framing, precisely: this is explicitly QUEUED for review
once work reaches that stage (near the end of the current, much
larger body of work still ahead) -- not something to scope in detail
now. This note exists so the idea and its real starting point aren't
lost between now and then, not as a finished design.

## The real idea, as given

The VM/Workbench already lets a person watch data flow through every
cell directly -- but that's confirmation *from inside* the same
process that ran the simulation. Alan's own real point: add a way to
confirm a design's output *externally* -- write a result to a real
file, independent of whatever process computed it, so trusting the
answer doesn't rest on trusting your own introspection of the run
that produced it.

## The real hook this connects to, confirmed directly, not assumed

`IcmV3Record` already has a real field for exactly this shape of
thing: `io_name` -- marking a cell as "a genuine external data entry/
exit point," with its own real design note stating plainly that
whether a marked cell is used for input or output is decided AT THE
POINT OF USE, not baked into the field itself, "so the same RAM cell
that takes a seed value in can just as naturally be read back out."
That's real, existing infrastructure this idea would use, not
something needing to be invented from scratch. And `IcmV3File.save()`/
`.load()` already do real Python file I/O for loading programs in the
first place -- writing a computed result back out through that same
kind of channel reuses a path that already exists.

## A real, useful connection worth remembering when this gets built

This whole session's own real bug-finding discipline has been doing a
version of this by hand, constantly -- nearly every real bug found
this week (`ashr`'s sign ordering, `icmp`'s DAG timing, `eq`/`ne`'s
width mismatch) was caught by comparing the VM's own computed value
against an independently-computed expected one, written as a separate
check in a throwaway test script each time. A real output-file
mechanism is that same comparison discipline, made a genuine, standing
capability instead of reinvented per test.

## Real, honest scope note, not yet resolved

This is a genuinely different capability from the Workbench's own
current, real scope (`workbench_scope.md`'s own "place, route, and
review an already-compiled model") -- closer to "a real way to run a
compiled program and collect its answer," which is its own real
feature needing its own real scoping pass when the time comes, not
something that falls out of the Workbench's existing job for free.

## Status

Queued for a real scoping pass later, near the end of the current,
much larger body of LaTeX/TRIX-family work still ahead -- not
resolved here. No RTL, no VM change, no file format change, nothing
built. This note exists only to hold the idea and its real starting
point (`io_name`, already built) until that point is reached.
