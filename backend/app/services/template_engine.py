"""Template engine — pure !{VAR_NAME} interpolation, no I/O."""
import re
from dataclasses import dataclass, field

VAR_PATTERN = re.compile(r"!\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass
class RenderResult:
    content: str
    warnings: list[str] = field(default_factory=list)


def render_template(template_content: str, variables: dict[str, str]) -> RenderResult:
    """Replace !{VAR_NAME} placeholders with variable values.

    - Resolved variables are substituted in-place.
    - Unresolved placeholders are preserved as-is and added to warnings.
    """
    warnings = []
    seen_unresolved = set()

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return variables[var_name]
        if var_name not in seen_unresolved:
            seen_unresolved.add(var_name)
            warnings.append(f"Unresolved variable: !{{{var_name}}}")
        return match.group(0)  # keep original placeholder

    result = VAR_PATTERN.sub(replacer, template_content)
    return RenderResult(content=result, warnings=warnings)


def extract_variable_names(template_content: str) -> list[str]:
    """Extract all unique variable names referenced in a template."""
    return list(dict.fromkeys(VAR_PATTERN.findall(template_content)))


def count_variable_references(template_content: str, var_name: str) -> int:
    """Count how many times !{var_name} appears in the template."""
    pattern = f"!{{{var_name}}}"
    return template_content.count(pattern)


def reverse_render(
    old_template: str,
    variables: dict[str, str],
    new_content: str,
) -> str:
    """Recover !{VAR} placeholders from edited content by comparing with old template.

    Algorithm:
    1. Parse old template into segments: alternating literal text and variable refs
    2. Use literal segments as anchors to find positions in new content (left-to-right)
    3. Between anchors, compare extracted text with variable's rendered value
       - Match -> restore !{VAR} placeholder
       - No match -> keep literal text
    4. If any anchor not found, return new_content as-is (fallback)
    """
    # Parse old template into segments
    segments: list[tuple[str, str]] = []
    last_end = 0
    for match in VAR_PATTERN.finditer(old_template):
        start, end = match.span()
        if start > last_end:
            segments.append(("literal", old_template[last_end:start]))
        var_name = match.group(1)
        segments.append(("var", var_name))
        last_end = end
    if last_end < len(old_template):
        segments.append(("literal", old_template[last_end:]))

    # No variables — return new content as-is
    if not any(s[0] == "var" for s in segments):
        return new_content

    # Build a list of anchor positions in new_content
    anchor_positions: list[tuple[int, int, int]] = []
    search_from = 0

    for i, (seg_type, seg_value) in enumerate(segments):
        if seg_type == "literal":
            pos = new_content.find(seg_value, search_from)
            if pos == -1:
                # Anchor not found — fallback
                return new_content
            anchor_positions.append((i, pos, pos + len(seg_value)))
            search_from = pos + len(seg_value)

    # Build result parts with anchor positions mapped
    result_parts: list[tuple[str, str, int | None, int | None]] = []
    anchor_map = {ap[0]: (ap[1], ap[2]) for ap in anchor_positions}

    for i, (seg_type, seg_value) in enumerate(segments):
        if seg_type == "literal":
            start, end = anchor_map[i]
            result_parts.append(("literal_anchor", seg_value, start, end))
        else:
            result_parts.append(("var", seg_value, None, None))

    # Reconstruct template from new_content
    output: list[str] = []
    new_idx = 0

    for idx, rp in enumerate(result_parts):
        if rp[0] == "literal_anchor":
            _type, text, start, end = rp
            output.append(text)
            new_idx = end
        else:
            _type, var_name, _, _ = rp
            # Find next literal anchor to determine region end
            next_anchor_start = None
            for j in range(idx + 1, len(result_parts)):
                if result_parts[j][0] == "literal_anchor":
                    next_anchor_start = result_parts[j][2]
                    break

            if next_anchor_start is None:
                region_end = len(new_content)
            else:
                region_end = next_anchor_start

            extracted = new_content[new_idx:region_end]
            rendered_value = variables.get(var_name)

            if rendered_value is not None and extracted == rendered_value:
                output.append(f"!{{{var_name}}}")
            else:
                if rendered_value is None:
                    # Unresolved variable — check if placeholder text is preserved
                    placeholder = f"!{{{var_name}}}"
                    if extracted == placeholder:
                        output.append(placeholder)
                    else:
                        output.append(extracted)
                else:
                    output.append(extracted)
            new_idx = region_end

    # Trailing content after last anchor
    if new_idx < len(new_content):
        output.append(new_content[new_idx:])

    return "".join(output)
