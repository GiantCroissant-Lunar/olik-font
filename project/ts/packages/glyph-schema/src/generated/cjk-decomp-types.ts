/**
 * Structured JSON form of the cjk-decomp dataset (https://github.com/amake/cjk-decomp).
 * Each entry maps a character to its operator + components per cjk-decomp's grammar. Atomic
 * characters have operator: null and components: [].
 */
export interface CJKDecomp {
    /**
     * Character → decomposition entry. Keys are single Unicode CJK characters.
     */
    entries: { [key: string]: Entry };
    /**
     * Schema version of THIS file (not upstream data).
     */
    schema_version: string;
    source:         Source;
}

export interface Entry {
    /**
     * Sub-character identifiers. Empty when atomic. May include numeric IDs for characters that
     * don't have Unicode codepoints.
     */
    components: string[];
    /**
     * cjk-decomp operator: lowercase letter(s) like 'a', 'c', 'b', 's', 'd', 'o', 't', 'ra',
     * 'str', 'r3tr', 'd/t'. null means atomic.
     */
    operator: null | string;
}

export interface Source {
    commit:        string;
    license:       string;
    retrieved_at?: Date;
    upstream:      string;
}
