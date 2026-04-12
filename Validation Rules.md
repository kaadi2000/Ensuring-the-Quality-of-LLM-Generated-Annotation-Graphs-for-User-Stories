## 1. Scope

### In scope
- Parse annotated JSON graph files
- Validate structure and required fields
- Validate references used in relations
- Validate metamodel compatibility:
  - Triggers: Persona -> Activity
  - Targets: Activity -> Entity
  - Contains: Entity -> Entity
- Report errors and warnings
- Prepare clean internal graph data for later Henshin export


## 2. Validation rules

### A. Syntax and parsing rules
- **R1** The file must be valid JSON.
- **R2** The top level must be a list of story annotations.
- **R3** Each story annotation must be a JSON object.

### B. Required field rules
For each story object:
- **R4** Required keys must exist:
  - `PID`
  - `Text`
  - `Persona`
  - `Action`
  - `Entity`
  - `Benefit`
  - `Triggers`
  - `Targets`
  - `Contains`
- **R5** `PID` must be a string.
- **R6** `Text` must be a string.
- **R7** `Benefit` must be a string.
- **R8** `Persona` must be a list of strings.
- **R9** `Action` must be an object with:
  - `Primary Action`: list of strings
  - `Secondary Action`: list of strings
- **R10** `Entity` must be an object with:
  - `Primary Entity`: list of strings
  - `Secondary Entity`: list of strings

### C. Relation format rules
- **R11** `Triggers`, `Targets`, and `Contains` must be lists.
- **R12** Each relation entry must be a 2-element list of strings.

### D. Graph consistency rules
Build three node sets:
- Personas
- Activities = all primary + secondary actions
- Entities = all primary + secondary entities

Then check:
- **R13** Every trigger source must exist in `Persona`.
- **R14** Every trigger target must exist in action nodes.
- **R15** Every target source must exist in action nodes.
- **R16** Every target target must exist in entity nodes.
- **R17** Every contains source must exist in entity nodes.
- **R18** Every contains target must exist in entity nodes.

### E. Quality and warning rules
These are warnings, not hard failures:
- **W1** Empty persona list
- **W2** Empty primary action list
- **W3** Empty primary entity list
- **W4** Exact duplicate labels in the same category
- **W5** Case-insensitive duplicate labels, for example `Staff member` vs `staff member`
- **W6** Suspiciously short labels such as `when`
- **W7** Duplicate relation pairs