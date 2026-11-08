"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

/** Tags live in three spaces; the backend sorts them when an issue is created. */
export type TagSpace = "geography" | "topics" | "affected_groups";

export const TAG_SPACES: TagSpace[] = ["geography", "topics", "affected_groups"];

const LABELS: Record<TagSpace, string> = {
  geography: "Geography",
  topics: "Topics",
  affected_groups: "Affected groups",
};

type Tagged = Partial<Record<TagSpace, string[]>>;

export type TagSelection = Record<TagSpace, string[]>;
export const EMPTY_SELECTION: TagSelection = { geography: [], topics: [], affected_groups: [] };

/** Distinct values per space, most used first, so common choices sit at the front. */
export function optionsFromIssues(issues: Tagged[]): Record<TagSpace, string[]> {
  const out = {} as Record<TagSpace, string[]>;
  for (const space of TAG_SPACES) {
    const counts = new Map<string, number>();
    for (const issue of issues) {
      for (const value of issue[space] ?? []) counts.set(value, (counts.get(value) ?? 0) + 1);
    }
    out[space] = [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([value]) => value);
  }
  return out;
}

/** OR within a space, AND across spaces. An empty space means no filter. */
export function matchesTags(issue: Tagged, selection: TagSelection): boolean {
  return TAG_SPACES.every((space) => {
    const wanted = selection[space];
    if (wanted.length === 0) return true;
    const own = issue[space] ?? [];
    return wanted.some((value) => own.includes(value));
  });
}

type DropdownProps = {
  space: TagSpace;
  options: string[];
  selected: string[];
  onChange: (next: string[]) => void;
};

function TagDropdown({ space, options, selected, onChange }: DropdownProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();
  const label = LABELS[space];

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const toggle = (value: string) =>
    onChange(selected.includes(value) ? selected.filter((v) => v !== value) : [...selected, value]);

  return (
    <div className="tagfilter__item" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="tagfilter__button"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        {label}
        {selected.length > 0 ? (
          <span className="tagfilter__count" aria-label={`${selected.length} selected`}>
            {selected.length}
          </span>
        ) : null}
        <span className="tagfilter__caret" aria-hidden="true" />
      </button>

      {open ? (
        <div id={panelId} className="tagfilter__panel" role="group" aria-label={`Filter by ${label.toLowerCase()}`}>
          {options.length === 0 ? (
            <p className="tagfilter__empty">No {label.toLowerCase()} yet. They appear as new issues are tagged.</p>
          ) : (
            <div className="chips">
              {options.map((value) => (
                <button
                  key={value}
                  type="button"
                  className="chip"
                  aria-pressed={selected.includes(value)}
                  onClick={() => toggle(value)}
                >
                  {value}
                </button>
              ))}
            </div>
          )}
          {selected.length > 0 ? (
            <button type="button" className="tagfilter__clear" onClick={() => onChange([])}>
              Clear {label.toLowerCase()}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

type Props = {
  issues: Tagged[];
  selection: TagSelection;
  onChange: (next: TagSelection) => void;
};

export function TagFilter({ issues, selection, onChange }: Props) {
  const options = useMemo(() => optionsFromIssues(issues), [issues]);
  const total = TAG_SPACES.reduce((sum, space) => sum + selection[space].length, 0);

  return (
    <div className="tagfilter">
      {TAG_SPACES.map((space) => (
        <TagDropdown
          key={space}
          space={space}
          options={options[space]}
          selected={selection[space]}
          onChange={(next) => onChange({ ...selection, [space]: next })}
        />
      ))}
      {total > 0 ? (
        <button type="button" className="tagfilter__clear" onClick={() => onChange(EMPTY_SELECTION)}>
          Clear all
        </button>
      ) : null}
    </div>
  );
}
