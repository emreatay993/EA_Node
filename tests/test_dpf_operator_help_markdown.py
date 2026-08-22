from __future__ import annotations

import textwrap
import unittest

from ea_node_editor.help._qt_markdown import prepare_for_qt


_SAMPLE_DOC = textwrap.dedent(
    """\
    ---
    category: logic
    ---

    # logic:ascending sort (fields container)

    ## Inputs

    | Input | Name | Expected type(s) | Description |
    |-------|-------|------------------|-------------|
    | <strong>Pin 0</strong> <br><span style="background-color:#d93025; color:white; padding:2px 6px; border-radius:3px; font-size:0.75em;">Required</span>|  fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) | field or fields container with only one field is expected |
    | <strong>Pin 1</strong>|  component_priority_table |[`vector<int32>`](../../core-concepts/dpf-types.md#standard-types) | component priority table (vector of int) |
    | <strong>Pin 2</strong>|  sort_by_scoping |[`bool`](../../core-concepts/dpf-types.md#standard-types) | if true, uses scoping to sort the field (default is false) |

    ## Outputs

    | Output |  Name | Expected type(s) | Description |
    |-------|------|------------------|-------------|
    |  **Pin 0**| fields_container |[`fields_container`](../../core-concepts/dpf-types.md#fields-container) |  |

    ## Examples

    <details>
    <summary>C++</summary>

    ```cpp
    #include "dpf_api.h"

    ansys::dpf::Operator op("ascending_sort_fc");
    ansys::dpf::FieldsContainer my_fields_container = op.getOutput<ansys::dpf::FieldsContainer>(0);
    ```
    </details>

    <details>
    <summary>CPython</summary>

    ```python
    import ansys.dpf.core as dpf

    op = dpf.operators.logic.ascending_sort_fc()
    ```
    </details>
    <br>
    """
)


def _extract_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.index(marker)
    rest = text[start + len(marker) :]
    next_heading = rest.find("\n## ")
    return rest if next_heading == -1 else rest[:next_heading]


def _table_rows(section: str) -> list[str]:
    rows = [line for line in section.splitlines() if line.startswith("|")]
    # Strip header and separator rows.
    return [row for row in rows[2:] if row.strip()]


class PrepareForQtTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = prepare_for_qt(_SAMPLE_DOC)

    def test_inputs_table_is_clean_four_column_markdown(self) -> None:
        inputs = _extract_section(self.output, "Inputs")
        rows = _table_rows(inputs)
        self.assertEqual(len(rows), 3, f"unexpected row count: {rows!r}")
        for row in rows:
            self.assertEqual(
                row.count("|"),
                5,
                f"expected 5 pipes per 4-column row, got: {row!r}",
            )
            self.assertNotIn("<strong>", row)
            self.assertNotIn("<span", row)
            self.assertNotIn("<br", row)
        self.assertIn("**Pin 0**", rows[0])
        self.assertIn("fields_container", rows[0])
        self.assertIn("**Pin 1**", rows[1])
        self.assertIn("component_priority_table", rows[1])
        self.assertIn("**Pin 2**", rows[2])
        self.assertIn("sort_by_scoping", rows[2])

    def test_outputs_row_retains_name(self) -> None:
        outputs = _extract_section(self.output, "Outputs")
        rows = _table_rows(outputs)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].count("|"), 5)
        self.assertIn("**Pin 0**", rows[0])
        self.assertIn("fields_container", rows[0])

    def test_no_html_remains_in_document(self) -> None:
        for needle in ("<strong>", "</strong>", "<span", "</span>", "<details>", "</details>", "<summary>", "</summary>"):
            self.assertNotIn(needle, self.output, f"{needle} leaked through")

    def test_details_examples_become_bold_label_plus_fence(self) -> None:
        self.assertIn("**C++**", self.output)
        self.assertIn("**CPython**", self.output)
        cpp_start = self.output.index("**C++**")
        python_start = self.output.index("**CPython**")
        cpp_block = self.output[cpp_start:python_start]
        self.assertIn("```cpp", cpp_block)
        self.assertIn('ansys::dpf::Operator op("ascending_sort_fc");', cpp_block)
        self.assertIn(
            "ansys::dpf::FieldsContainer my_fields_container = "
            "op.getOutput<ansys::dpf::FieldsContainer>(0);",
            cpp_block,
        )
        self.assertIn("```\n", cpp_block)

    def test_idempotent(self) -> None:
        self.assertEqual(prepare_for_qt(self.output), self.output)

    def test_plain_markdown_passes_through(self) -> None:
        plain = "# Heading\n\nParagraph text with a [link](x.md).\n\n```py\nprint('hi')\n```\n"
        self.assertEqual(prepare_for_qt(plain), plain)

    def test_empty_input(self) -> None:
        self.assertEqual(prepare_for_qt(""), "")


if __name__ == "__main__":
    unittest.main()
