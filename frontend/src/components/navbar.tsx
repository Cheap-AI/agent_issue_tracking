"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Menu, MenuItem, HoveredLink, ProductItem } from "./ui/navbar-menu";
import { cn } from "../lib/utils";

export function Navbar({ className }: { className?: string }) {
  const [active, setActive] = useState<string | null>(null);

  return (
    <div
      className={cn("fixed inset-x-0 top-0 z-50 mx-auto w-full", className)}
    >
      <Menu setActive={setActive}>
        <MenuItem setActive={setActive} active={active} item="Home">
          <div className="flex flex-col space-y-4 text-sm">
            <HoveredLink href="/">
              Dashboard
            </HoveredLink>
          </div>
        </MenuItem>

        <MenuItem setActive={setActive} active={active} item="Issues">
          <div className="flex flex-col space-y-4 text-sm">
            <HoveredLink href="/">
              View All Issues
            </HoveredLink>
            <HoveredLink href="/">
              Create New Issue
            </HoveredLink>
            <HoveredLink href="/">
              My Tickets
            </HoveredLink>
          </div>
        </MenuItem>

        <MenuItem setActive={setActive} active={active} item="Research">
          <div className="flex flex-col space-y-4 text-sm">
            <HoveredLink href="/">
              Generate Draft
            </HoveredLink>
            <HoveredLink href="/">
              Browse Topics
            </HoveredLink>
            <HoveredLink href="/">
              Research History
            </HoveredLink>
          </div>
        </MenuItem>

        <MenuItem setActive={setActive} active={active} item="About">
          <div className="flex flex-col space-y-4 text-sm">
            <HoveredLink href="/about">
              About Platform
            </HoveredLink>
            <HoveredLink href="/">
              Documentation
            </HoveredLink>
            <HoveredLink href="/">
              Support
            </HoveredLink>
          </div>
        </MenuItem>
      </Menu>
    </div>
  );
}
