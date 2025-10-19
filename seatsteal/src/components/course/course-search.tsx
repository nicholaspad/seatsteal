import { useState, useEffect, useCallback, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface CourseSearchProps {
  value?: string;
  onValueChange: (query: string) => void;
  placeholder?: string;
  className?: string;
  debounceMs?: number;
}

export function CourseSearch({
  value = "",
  onValueChange,
  placeholder = "Search courses...",
  className,
  debounceMs = 400,
}: CourseSearchProps) {
  const [inputValue, setInputValue] = useState(value);
  const [isDebouncing, setIsDebouncing] = useState(false);
  const lastEmittedValueRef = useRef(value);

  // Debounced callback to emit the search query
  const debouncedOnValueChange = useCallback(
    (query: string) => {
      const timeoutId = setTimeout(() => {
        onValueChange(query);
        lastEmittedValueRef.current = query;
        setIsDebouncing(false);
      }, debounceMs);

      return () => clearTimeout(timeoutId);
    },
    [onValueChange, debounceMs],
  );

  // Update input value when external value changes, but only if it's different from what we last emitted
  useEffect(() => {
    if (value !== lastEmittedValueRef.current) {
      setInputValue(value);
      lastEmittedValueRef.current = value;
    }
  }, [value]);

  // Handle input changes with debouncing
  useEffect(() => {
    if (inputValue !== lastEmittedValueRef.current) {
      setIsDebouncing(true);
      const cleanup = debouncedOnValueChange(inputValue);
      return cleanup;
    }
  }, [inputValue, debouncedOnValueChange]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  const handleClear = () => {
    setInputValue("");
    onValueChange("");
    lastEmittedValueRef.current = "";
    setIsDebouncing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      handleClear();
    }
  };

  return (
    <div className={cn("relative flex items-center", className)}>
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={cn("pl-10 pr-10", isDebouncing && "opacity-75")}
          aria-label="Search courses"
        />
        {inputValue && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleClear}
            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0 hover:bg-muted"
            aria-label="Clear search"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    </div>
  );
}
