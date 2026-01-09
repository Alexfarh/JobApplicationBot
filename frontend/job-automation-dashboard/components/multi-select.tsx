"use client"

import * as React from "react"
import { Check, ChevronsUpDown, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

export interface MultiSelectProps {
  options: string[]
  selected: string[]
  onSelectionChange: (selected: string[]) => void
  placeholder?: string
  searchPlaceholder?: string
}

export function MultiSelect({
  options,
  selected,
  onSelectionChange,
  placeholder = "Select items...",
  searchPlaceholder = "Search...",
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState("")

  const filteredOptions = options.filter((option) =>
    option.toLowerCase().includes(search.toLowerCase())
  )

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onSelectionChange(selected.filter((item) => item !== option))
    } else {
      onSelectionChange([...selected, option])
    }
  }

  const removeOption = (option: string) => {
    onSelectionChange(selected.filter((item) => item !== option))
  }

  return (
    <div className="w-full">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between bg-slate-800 border-slate-600 text-slate-200 hover:bg-slate-700"
          >
            <span className="truncate">
              {selected.length === 0
                ? placeholder
                : `${selected.length} selected`}
            </span>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-full p-0 bg-slate-800 border-slate-700">
          <Command className="bg-slate-800">
            <CommandInput
              placeholder={searchPlaceholder}
              value={search}
              onValueChange={setSearch}
              className="text-slate-200 placeholder-slate-500"
            />
            <CommandEmpty className="text-slate-400 py-6 text-center">
              No results found
            </CommandEmpty>
            <CommandList className="bg-slate-800">
              <CommandGroup className="overflow-hidden">
                {filteredOptions.map((option) => (
                  <CommandItem
                    key={option}
                    value={option}
                    onSelect={() => toggleOption(option)}
                    className="text-slate-200 hover:bg-slate-700 cursor-pointer"
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selected.includes(option)
                          ? "opacity-100"
                          : "opacity-0"
                      )}
                    />
                    {option}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* Selected items display */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {selected.map((item) => (
            <div
              key={item}
              className="flex items-center gap-1 px-2 py-1 bg-blue-500/20 text-blue-300 rounded-md text-sm"
            >
              <span>{item}</span>
              <button
                onClick={() => removeOption(item)}
                className="ml-1 hover:text-blue-200"
                type="button"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
