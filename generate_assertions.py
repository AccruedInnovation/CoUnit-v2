"""Generate the R3 assertion implementation, preserving the 1.2.0.3 public API.

Run with --check for a read-only regeneration and source-contract check.
Native compiler/runtime qualification is separate from this source check.
"""
from pathlib import Path
import argparse
import csv
import re

HERE = Path(__file__).resolve().parent
REPO = HERE if (HERE / 'docs').is_dir() else HERE.parents[2]
ROOT = HERE / "PlaintextExport/Unit Test Framework for CODESYS"
OLD = (HERE / "compatibility/1.2.0.3/PlaintextExport") if (HERE / "compatibility").is_dir() else HERE.parent / "1.2.0.3/PlaintextExport"
SUITE = ROOT / "POUs/FB_TestSuite"
FILES = {}


def emit(path, text):
    FILES[path] = text.strip() + "\n"


def method(name, declaration, body):
    emit(SUITE / name / (name + ".DEC.exp"), declaration)
    emit(SUITE / name / (name + ".IMP.exp"), body)


def block(kind, fields):
    return kind + "\n" + "\n".join("\t" + f + ";" for f in fields) + "\nEND_VAR\n" if fields else ""


def helper(name, result, inputs, locals_, body, outputs=()):
    method(name, f"METHOD PRIVATE {name}" + (f" : {result}" if result else "") + "\n"
           + block("VAR_INPUT", inputs) + block("VAR_OUTPUT", outputs) + block("VAR", locals_), body)


def original_header(row):
    text = (OLD / row["source_export_path"]).read_text(encoding="utf-8-sig")
    text = re.sub(r"\(\*.*?\*\)", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"\bVAR\b.*?END_VAR", "", text, flags=re.S)
    text = re.sub(r"\{[^}]*\}", "", text)
    assert " ".join(text.split()) == row["public_signature"], row["method"]
    return "\n".join(("\t" + line.strip() if line.startswith((" ", "\t")) else line.strip())
                     for line in text.strip().splitlines() if line.strip()) + "\n"


emit(ROOT / "DUTs/ST_CoUnitComparisonResult/ST_CoUnitComparisonResult.DEC.exp", """
TYPE ST_CoUnitComparisonResult :
STRUCT
	Passed : BOOL;
	ArgumentError : BOOL;
	ExpectedText : T_MaxString;
	ActualText : T_MaxString;
	DiagnosticSuffix : T_MaxString;
END_STRUCT
END_TYPE
""")

helper("BeginAssertion", "BOOL", [], ["_execute : BOOL"], """
BeginAssertion := FALSE;
TestIndex := 0;
Ordinal := 0;
IF NOT GVL_coUnit.coUnitRunner.ValidateContext(Suite := THIS, RequireTest := TRUE, TestIndex => TestIndex, Execute => _execute) THEN
	RETURN;
END_IF
IF NOT _execute THEN
	RETURN;
END_IF
IF NOT GVL_coUnit.coUnitRunner.ConsumeAssertionBudget() THEN
	RETURN;
END_IF
TestRecords[TestIndex].InvocationOrdinal := TestRecords[TestIndex].InvocationOrdinal + 1;
TestRecords[TestIndex].MaxAssertionsPerInvocation := MAX(TestRecords[TestIndex].MaxAssertionsPerInvocation, TestRecords[TestIndex].InvocationOrdinal);
Ordinal := TestRecords[TestIndex].InvocationOrdinal;
BeginAssertion := TRUE;
""", ["TestIndex : UINT", "Ordinal : UDINT"])

helper("BoundedJoin", "T_MaxString", ["LeftText : T_MaxString", "RightText : T_MaxString", "AlreadyTruncated : BOOL"],
       ["_left : POINTER TO BYTE", "_right : POINTER TO BYTE", "_dest : POINTER TO BYTE", "_marker : T_MaxString := '...<truncated>'",
        "_mark : POINTER TO BYTE", "_leftLen : UINT", "_rightLen : UINT", "_length : UINT", "_keep : UINT", "_i : UINT",
        "_start : UINT", "_needed : UINT", "_lead : BYTE"], """
Truncated := AlreadyTruncated;
IF AlreadyTruncated THEN BoundedJoin := LeftText; RETURN; END_IF
_left := ADR(LeftText);
_right := ADR(RightText);
_dest := ADR(BoundedJoin);
_mark := ADR(_marker);
_leftLen := 0;
_rightLen := 0;
WHILE _leftLen < 255 DO
	IF _left[_leftLen] = 0 THEN EXIT; END_IF
	_leftLen := _leftLen + 1;
END_WHILE
WHILE _rightLen < 255 DO
	IF _right[_rightLen] = 0 THEN EXIT; END_IF
	_rightLen := _rightLen + 1;
END_WHILE
_length := _leftLen + _rightLen;
Truncated := _length > 255;
_keep := _length;
IF _length > 255 THEN _keep := 241; END_IF
_i := 0;
WHILE _i < _keep DO
	IF _i < _leftLen THEN _dest[_i] := _left[_i]; ELSE _dest[_i] := _right[_i - _leftLen]; END_IF
	_i := _i + 1;
END_WHILE
IF _length > 255 THEN
	(* The integration preflight binds the native STRING mode in the shared configuration. *)
	IF GVL_coUnit.StringIsUtf8 AND (_keep > 0) THEN
		_start := _keep - 1;
		WHILE _start > 0 DO
			IF (_dest[_start] AND BYTE#16#C0) <> BYTE#16#80 THEN EXIT; END_IF
			_start := _start - 1;
		END_WHILE
		_lead := _dest[_start];
		_needed := 1;
		IF (_lead AND BYTE#16#E0) = BYTE#16#C0 THEN _needed := 2;
		ELSIF (_lead AND BYTE#16#F0) = BYTE#16#E0 THEN _needed := 3;
		ELSIF (_lead AND BYTE#16#F8) = BYTE#16#F0 THEN _needed := 4;
		END_IF
		IF (_keep - _start) < _needed THEN _keep := _start; END_IF
	END_IF
	FOR _i := 0 TO 13 DO _dest[_keep + _i] := _mark[_i]; END_FOR
	_keep := _keep + 14;
END_IF
_dest[_keep] := 0;
""", ["Truncated : BOOL"])

helper("RecordAssertionOutcome", "", ["TestIndex : UINT", "Ordinal : UDINT", "AssertionType : E_AssertionType", "Message : T_MaxString", "Comparison : ST_CoUnitComparisonResult"],
       ["_message : T_MaxString", "_log : T_MaxString", "_logResult : DINT", "_messageTruncated : BOOL", "_logTruncated : BOOL"], """
IF Comparison.Passed THEN RETURN; END_IF
IF (TestIndex = 0) OR (TestIndex > NumberOfTests) THEN
	GVL_coUnit.coUnitRunner.FrameworkError(Reason := 'Invalid assertion outcome index');
	RETURN;
END_IF
TestRecords[TestIndex].HasFailure := TRUE;
IF TestRecords[TestIndex].FirstFailure.IsSet THEN RETURN; END_IF
_message := Message;
_messageTruncated := FALSE;
IF Comparison.ArgumentError THEN
	_message := BoundedJoin(LeftText := 'Invalid assertion argument: ', RightText := Message);
END_IF
IF LEN(Comparison.DiagnosticSuffix) > 0 THEN
	_message := BoundedJoin(LeftText := _message, RightText := ' | ');
	_message := BoundedJoin(LeftText := _message, RightText := Comparison.DiagnosticSuffix);
END_IF
TestRecords[TestIndex].FirstFailure.AssertionType := AssertionType;
TestRecords[TestIndex].FirstFailure.Message := _message;
TestRecords[TestIndex].FirstFailure.ExpectedText := Comparison.ExpectedText;
TestRecords[TestIndex].FirstFailure.ActualText := Comparison.ActualText;
TestRecords[TestIndex].FirstFailure.IsSet := TRUE;
(* Commit truth before the non-authoritative, first-failure-only diagnostic effect. *)
_logTruncated := FALSE;
_log := BoundedJoin(LeftText := 'FAILED: ', RightText := TestRecords[TestIndex].CanonicalName);
_log := BoundedJoin(LeftText := _log, RightText := CONCAT(' #', UDINT_TO_STRING(Ordinal)));
_log := BoundedJoin(LeftText := _log, RightText := ' | ');
_log := BoundedJoin(LeftText := _log, RightText := _message);
_log := BoundedJoin(LeftText := _log, RightText := ' | expected=');
_log := BoundedJoin(LeftText := _log, RightText := Comparison.ExpectedText);
_log := BoundedJoin(LeftText := _log, RightText := ' | actual=');
_log := BoundedJoin(LeftText := _log, RightText := Comparison.ActualText);
_logResult := WRITE_DEVICE_LOG(msgCtrlMask := UDINT_TO_DWORD(CmpLog.LogClass.LOG_ERROR), msgFmtStr := '%s', strArg := _log);
""")

# Carry truncation only within a single diagnostic composition, not in retained state.
outcome_path = SUITE / "RecordAssertionOutcome/RecordAssertionOutcome.IMP.exp"
outcome_lines = FILES[outcome_path].splitlines()
for index, line in enumerate(outcome_lines):
    if ":= BoundedJoin(" in line:
        flag = "_messageTruncated" if line.lstrip().startswith("_message :=") else "_logTruncated"
        outcome_lines[index] = line[:-2] + f", AlreadyTruncated := {flag}, Truncated => {flag});"
emit(outcome_path, "\n".join(outcome_lines))

for typ, bits, exponent, fraction, sign in [
    ("REAL", "DWORD", "7F800000", "007FFFFF", "80000000"),
    ("LREAL", "LWORD", "7FF0000000000000", "000FFFFFFFFFFFFF", "8000000000000000")]:
    # No operand is inspected using FP operations until all raw classifications are done.
    helper("Compare_" + typ, "BOOL", [f"Expected : {typ}", f"Actual : {typ}", f"Delta : {typ}"],
           [f"_expectedBits : {bits}", f"_actualBits : {bits}", f"_deltaBits : {bits}", "_expectedInf : BOOL", "_actualInf : BOOL",
            f"_a : {typ}", f"_b : {typ}"], f"""
Compare_{typ} := FALSE;
ArgumentError := FALSE;
MEMCPY(destAddr := ADR(_expectedBits), srcAddr := ADR(Expected), n := SIZEOF({typ}));
MEMCPY(destAddr := ADR(_actualBits), srcAddr := ADR(Actual), n := SIZEOF({typ}));
MEMCPY(destAddr := ADR(_deltaBits), srcAddr := ADR(Delta), n := SIZEOF({typ}));
IF ((_deltaBits AND {bits}#16#{exponent}) = {bits}#16#{exponent}) AND ((_deltaBits AND {bits}#16#{fraction}) <> 0) THEN
	ArgumentError := TRUE;
	RETURN;
END_IF
IF ((_deltaBits AND {bits}#16#{sign}) <> 0) AND ((_deltaBits AND NOT {bits}#16#{sign}) <> 0) THEN
	ArgumentError := TRUE;
	RETURN;
END_IF
IF (((_expectedBits AND {bits}#16#{exponent}) = {bits}#16#{exponent}) AND ((_expectedBits AND {bits}#16#{fraction}) <> 0))
	OR (((_actualBits AND {bits}#16#{exponent}) = {bits}#16#{exponent}) AND ((_actualBits AND {bits}#16#{fraction}) <> 0)) THEN RETURN; END_IF
_expectedInf := (_expectedBits AND NOT {bits}#16#{sign}) = {bits}#16#{exponent};
_actualInf := (_actualBits AND NOT {bits}#16#{sign}) = {bits}#16#{exponent};
IF _expectedInf OR _actualInf THEN
	Compare_{typ} := _expectedInf AND _actualInf AND ((_expectedBits AND {bits}#16#{sign}) = (_actualBits AND {bits}#16#{sign}));
	RETURN;
END_IF
IF _deltaBits = {bits}#16#{exponent} THEN Compare_{typ} := TRUE; RETURN; END_IF
IF Expected = Actual THEN Compare_{typ} := TRUE; RETURN; END_IF
IF (_expectedBits AND {bits}#16#{sign}) <> (_actualBits AND {bits}#16#{sign}) THEN
	_a := ABS(Expected);
	_b := ABS(Actual);
	IF Delta < _a THEN RETURN; END_IF
	Compare_{typ} := _b <= (Delta - _a);
ELSE
	Compare_{typ} := ABS(Expected - Actual) <= Delta;
END_IF
""", ["ArgumentError : BOOL"])
    helper("Text_" + typ, "T_MaxString", [f"Value : {typ}"], [f"_bits : {bits}"], f"""
MEMCPY(destAddr := ADR(_bits), srcAddr := ADR(Value), n := SIZEOF({typ}));
IF (_bits AND {bits}#16#{exponent}) = {bits}#16#{exponent} THEN
	IF (_bits AND {bits}#16#{fraction}) <> 0 THEN Text_{typ} := 'NaN';
	ELSIF (_bits AND {bits}#16#{sign}) <> 0 THEN Text_{typ} := '-Infinity';
	ELSE Text_{typ} := '+Infinity'; END_IF
ELSE
	Text_{typ} := {typ}_TO_STRING(Value);
END_IF
""")


def text_value(typ, value):
    if typ in ("REAL", "LREAL"):
        return f"Text_{typ}(Value := {value})"
    if typ == "STRING":
        return value
    conversion = {"DATE_AND_TIME": "DT", "TIME_OF_DAY": "TOD"}.get(typ, typ)
    return f"{conversion}_TO_STRING({value})"


primitive_types = ["BOOL", "BYTE", "WORD", "DWORD", "LWORD", "SINT", "INT", "DINT", "LINT", "USINT", "UINT", "UDINT", "ULINT", "REAL", "LREAL", "TIME", "LTIME", "DATE", "DATE_AND_TIME", "TIME_OF_DAY"]
any_locals = ["_result : ST_CoUnitComparisonResult", "_i : DINT", "_expectedLength : DINT", "_actualLength : DINT", "_expectedUnit : WORD", "_actualUnit : WORD", "_unitSize : DINT", "_mismatch : BOOL"]
for typ in primitive_types:
    any_locals.extend([f"_expected{typ} : {typ}", f"_actual{typ} : {typ}"])
any_body = """
_result.Passed := FALSE;
_result.ArgumentError := FALSE;
_result.ExpectedText := '';
_result.ActualText := '';
_result.DiagnosticSuffix := '';
IF (ExpectedData = 0) OR (ActualData = 0) THEN
	_result.ArgumentError := TRUE;
	_result.DiagnosticSuffix := 'Null ANY data pointer';
ELSIF (ExpectedSize < 0) OR (ActualSize < 0) THEN
	_result.ArgumentError := TRUE;
	_result.DiagnosticSuffix := 'Negative ANY descriptor size';
ELSIF ExpectedClass <> ActualClass THEN
	_result.ExpectedText := CONCAT('type=', DINT_TO_STRING(ExpectedClass));
	_result.ActualText := CONCAT('type=', DINT_TO_STRING(ActualClass));
ELSE
	IF (ExpectedClass = TO_DINT(IBaseLibrary.TypeClass.TYPE_STRING)) OR (ExpectedClass = TO_DINT(IBaseLibrary.TypeClass.TYPE_WSTRING)) THEN
		_unitSize := 1;
		IF ExpectedClass = TO_DINT(IBaseLibrary.TypeClass.TYPE_WSTRING) THEN _unitSize := SIZEOF(WORD); END_IF
		IF ((ExpectedSize MOD _unitSize) <> 0) OR ((ActualSize MOD _unitSize) <> 0) THEN
			_result.ArgumentError := TRUE;
			_result.DiagnosticSuffix := 'WSTRING size is not a whole native WORD code unit';
		ELSE
			(* Find both terminators independently: an early mismatch must not hide a malformed descriptor. *)
			_expectedLength := 0;
			WHILE _expectedLength < ExpectedSize DO
				_expectedUnit := 0;
				MEMCPY(destAddr := ADR(_expectedUnit), srcAddr := ExpectedData + _expectedLength, n := DINT_TO_UDINT(_unitSize));
				IF _expectedUnit = 0 THEN EXIT; END_IF
				_expectedLength := _expectedLength + _unitSize;
			END_WHILE
			_actualLength := 0;
			WHILE _actualLength < ActualSize DO
				_actualUnit := 0;
				MEMCPY(destAddr := ADR(_actualUnit), srcAddr := ActualData + _actualLength, n := DINT_TO_UDINT(_unitSize));
				IF _actualUnit = 0 THEN EXIT; END_IF
				_actualLength := _actualLength + _unitSize;
			END_WHILE
			IF (_expectedLength = ExpectedSize) OR (_actualLength = ActualSize) THEN
				_result.ArgumentError := TRUE;
				_result.DiagnosticSuffix := 'Missing bounded STRING/WSTRING terminator';
			ELSE
				_result.Passed := _expectedLength = _actualLength;
				_i := 0;
				_mismatch := FALSE;
				WHILE _i < MIN(_expectedLength, _actualLength) DO
					_expectedUnit := 0;
					_actualUnit := 0;
					MEMCPY(destAddr := ADR(_expectedUnit), srcAddr := ExpectedData + _i, n := DINT_TO_UDINT(_unitSize));
					MEMCPY(destAddr := ADR(_actualUnit), srcAddr := ActualData + _i, n := DINT_TO_UDINT(_unitSize));
					IF _expectedUnit <> _actualUnit THEN _result.Passed := FALSE; _mismatch := TRUE; EXIT; END_IF
					_i := _i + _unitSize;
				END_WHILE
				IF NOT _result.Passed THEN
					_result.ExpectedText := CONCAT('code units=', DINT_TO_STRING(_expectedLength / _unitSize));
					_result.ActualText := CONCAT('code units=', DINT_TO_STRING(_actualLength / _unitSize));
					IF _mismatch THEN
						_result.ExpectedText := CONCAT(CONCAT(_result.ExpectedText, ', unit='), WORD_TO_STRING(_expectedUnit));
						_result.ActualText := CONCAT(CONCAT(_result.ActualText, ', unit='), WORD_TO_STRING(_actualUnit));
						_result.DiagnosticSuffix := CONCAT('First differing code-unit offset=', DINT_TO_STRING(_i / _unitSize));
					END_IF
				END_IF
			END_IF
		END_IF
"""
for typ in primitive_types:
    enum = {"DATE_AND_TIME": "DATEANDTIME", "TIME_OF_DAY": "TIMEOFDAY"}.get(typ, typ)
    any_body += f"""
	ELSIF ExpectedClass = TO_DINT(IBaseLibrary.TypeClass.TYPE_{enum}) THEN
		IF (ExpectedSize <> SIZEOF({typ})) OR (ActualSize <> SIZEOF({typ})) THEN
			_result.ArgumentError := TRUE;
			_result.DiagnosticSuffix := 'Invalid {typ} ANY descriptor size';
		ELSE
			MEMCPY(destAddr := ADR(_expected{typ}), srcAddr := ExpectedData, n := SIZEOF({typ}));
			MEMCPY(destAddr := ADR(_actual{typ}), srcAddr := ActualData, n := SIZEOF({typ}));
"""
    if typ in ("REAL", "LREAL"):
        any_body += f"\t\t\t_result.Passed := Compare_{typ}(Expected := _expected{typ}, Actual := _actual{typ}, Delta := {typ}#0.0, ArgumentError => _result.ArgumentError);\n"
    else:
        any_body += f"\t\t\t_result.Passed := _expected{typ} = _actual{typ};\n"
    any_body += f"""
			IF NOT _result.Passed THEN
				_result.ExpectedText := {text_value(typ, '_expected' + typ)};
				_result.ActualText := {text_value(typ, '_actual' + typ)};
			END_IF
		END_IF
"""
any_body += """
	ELSIF ExpectedSize <> ActualSize THEN
		_result.ExpectedText := CONCAT('bytes=', DINT_TO_STRING(ExpectedSize));
		_result.ActualText := CONCAT('bytes=', DINT_TO_STRING(ActualSize));
	ELSE
		_result.Passed := TRUE;
		_i := 0;
		WHILE _i < ExpectedSize DO
			IF ExpectedData[_i] <> ActualData[_i] THEN
				_result.Passed := FALSE;
				_result.ExpectedText := BYTE_TO_STRING(ExpectedData[_i]);
				_result.ActualText := BYTE_TO_STRING(ActualData[_i]);
				_result.DiagnosticSuffix := CONCAT('First differing representation byte=', DINT_TO_STRING(_i));
				EXIT;
			END_IF
			_i := _i + 1;
		END_WHILE
	END_IF
END_IF
CompareAny := _result;
"""
helper("CompareAny", "ST_CoUnitComparisonResult",
       ["ExpectedData : POINTER TO BYTE", "ActualData : POINTER TO BYTE", "ExpectedSize : DINT", "ActualSize : DINT", "ExpectedClass : DINT", "ActualClass : DINT"], any_locals, any_body)

rows = list(csv.DictReader((REPO / "docs/CoUnit-PRD-Suite-R3/PRD-COU-02/contracts/assertion-family-map.csv").open()))
assert len(rows) == len({r["method"] for r in rows}) == 44
enum_source = (OLD / "Unit Test Framework for CODESYS/DUTs/E_AssertionType/E_AssertionType.DEC.exp").read_text(encoding="utf-8-sig")
assertion_types = set(re.findall(r"\bType_\w+\b", enum_source))
common_locals = ["_testIndex : UINT", "_ordinal : UDINT", "_result : ST_CoUnitComparisonResult"]
for row in rows:
    name = row["method"]
    is_array = name.startswith("AssertArray")
    typ = name.rsplit("_", 1)[-1]
    if name.startswith("AssertEquals_"):
        typ = name[len("AssertEquals_"):]
    enum = "Type_" + typ
    locals_ = list(common_locals)
    body = """IF NOT BeginAssertion(TestIndex => _testIndex, Ordinal => _ordinal) THEN RETURN; END_IF
_result.Passed := FALSE;
_result.ArgumentError := FALSE;
_result.ExpectedText := '';
_result.ActualText := '';
_result.DiagnosticSuffix := '';
"""
    if name == "AssertEquals":
        enum = "Type_ANY"
        body += "_result := CompareAny(ExpectedData := Expected.pValue, ActualData := Actual.pValue, ExpectedSize := Expected.diSize, ActualSize := Actual.diSize, ExpectedClass := UDINT_TO_DINT(Expected.TypeClass), ActualClass := UDINT_TO_DINT(Actual.TypeClass));\n"
    elif name in ("AssertTrue", "AssertFalse"):
        enum = "Type_BOOL"
        body += f"_result.Passed := {'Condition' if name == 'AssertTrue' else 'NOT Condition'};\nIF NOT _result.Passed THEN\n\t_result.ExpectedText := '{'TRUE' if name == 'AssertTrue' else 'FALSE'}';\n\t_result.ActualText := BOOL_TO_STRING(Condition);\nEND_IF\n"
    elif is_array:
        dims = 2 if "2d" in name else 3 if "3d" in name else 1
        enum = "Type_Array" + (str(dims) + "D" if dims > 1 else "") + "_" + typ
        locals_ += [f"_expectedLower : ARRAY[1..{dims}] OF DINT", f"_actualLower : ARRAY[1..{dims}] OF DINT", f"_extent : ARRAY[1..{dims}] OF LINT", f"_actualExtent : ARRAY[1..{dims}] OF LINT", f"_offset : ARRAY[1..{dims}] OF LINT", "_shapeMatches : BOOL", "_elementEqual : BOOL", "_argumentError : BOOL"]
        body += "_shapeMatches := TRUE;\n"
        for d in range(1, dims + 1):
            body += f"""_expectedLower[{d}] := LOWER_BOUND(Expecteds, {d});
_actualLower[{d}] := LOWER_BOUND(Actuals, {d});
_extent[{d}] := DINT_TO_LINT(UPPER_BOUND(Expecteds, {d})) - DINT_TO_LINT(_expectedLower[{d}]) + 1;
_actualExtent[{d}] := DINT_TO_LINT(UPPER_BOUND(Actuals, {d})) - DINT_TO_LINT(_actualLower[{d}]) + 1;
IF _extent[{d}] <> _actualExtent[{d}] THEN _shapeMatches := FALSE; END_IF
"""
        body += "IF NOT _shapeMatches THEN\n\t_result.ExpectedText := 'extents=';\n\t_result.ActualText := 'extents=';\n"
        for d in range(1, dims + 1):
            body += f"\t_result.ExpectedText := CONCAT(_result.ExpectedText, LINT_TO_STRING(_extent[{d}]));\n\t_result.ActualText := CONCAT(_result.ActualText, LINT_TO_STRING(_actualExtent[{d}]));\n"
            if d != dims:
                body += "\t_result.ExpectedText := CONCAT(_result.ExpectedText, ',');\n\t_result.ActualText := CONCAT(_result.ActualText, ',');\n"
        body += "ELSE\n\t_result.Passed := TRUE;\n"
        for d in range(1, dims + 1):
            body += "\t" * d + f"_offset[{d}] := 0;\n" + "\t" * d + f"WHILE _offset[{d}] < _extent[{d}] DO\n"
        e = "Expecteds[" + ", ".join(f"LINT_TO_DINT(DINT_TO_LINT(_expectedLower[{d}]) + _offset[{d}])" for d in range(1, dims + 1)) + "]"
        a = "Actuals[" + ", ".join(f"LINT_TO_DINT(DINT_TO_LINT(_actualLower[{d}]) + _offset[{d}])" for d in range(1, dims + 1)) + "]"
        indent = "\t" * (dims + 1)
        if typ in ("REAL", "LREAL"):
            body += indent + f"_elementEqual := Compare_{typ}(Expected := {e}, Actual := {a}, Delta := Delta, ArgumentError => _argumentError);\n" + indent + "_result.ArgumentError := _argumentError;\n"
        else:
            body += indent + f"_elementEqual := {e} = {a};\n"
        body += indent + "IF NOT _elementEqual THEN\n" + indent + "\t_result.Passed := FALSE;\n"
        body += indent + f"\t_result.ExpectedText := {text_value(typ, e)};\n" + indent + f"\t_result.ActualText := {text_value(typ, a)};\n" + indent + "\t_result.DiagnosticSuffix := 'First mismatch at logical offset=';\n"
        for d in range(1, dims + 1):
            body += indent + f"\t_result.DiagnosticSuffix := CONCAT(_result.DiagnosticSuffix, LINT_TO_STRING(_offset[{d}]));\n"
            if d != dims:
                body += indent + "\t_result.DiagnosticSuffix := CONCAT(_result.DiagnosticSuffix, ',');\n"
        body += indent + "\tEXIT;\n" + indent + "END_IF\n"
        for d in range(dims, 0, -1):
            body += "\t" * (d + 1) + "IF NOT _result.Passed THEN EXIT; END_IF\n"
            body += "\t" * (d + 1) + f"_offset[{d}] := _offset[{d}] + 1;\n" + "\t" * d + "END_WHILE\n"
        body += "END_IF\n"
    elif typ == "WSTRING":
        body += "_result := CompareAny(ExpectedData := ADR(Expected), ActualData := ADR(Actual), ExpectedSize := SIZEOF(Expected), ActualSize := SIZEOF(Actual), ExpectedClass := TO_DINT(IBaseLibrary.TypeClass.TYPE_WSTRING), ActualClass := TO_DINT(IBaseLibrary.TypeClass.TYPE_WSTRING));\n"
    else:
        if typ in ("REAL", "LREAL"):
            body += f"_result.Passed := Compare_{typ}(Expected := Expected, Actual := Actual, Delta := Delta, ArgumentError => _result.ArgumentError);\n"
        else:
            body += "_result.Passed := Expected = Actual;\n"
        body += f"IF NOT _result.Passed THEN\n\t_result.ExpectedText := {text_value(typ, 'Expected')};\n\t_result.ActualText := {text_value(typ, 'Actual')};\nEND_IF\n"
    if typ in ("REAL", "LREAL"):
        body += "IF _result.ArgumentError THEN _result.DiagnosticSuffix := 'Delta must be nonnegative and not NaN'; END_IF\n"
    assert enum in assertion_types, (name, enum)
    body += f"RecordAssertionOutcome(TestIndex := _testIndex, Ordinal := _ordinal, AssertionType := E_AssertionType.{enum}, Message := Message, Comparison := _result);\n"
    assert body.count("BeginAssertion(") == 1 and body.count("RecordAssertionOutcome(") == 1
    assert not re.search(r"\bAssert\w*\s*\(", body), name
    method(name, original_header(row) + block("VAR", locals_), body)

method("CalculateAndSetNumberOfAssertsForTest", """METHOD INTERNAL CalculateAndSetNumberOfAssertsForTest
VAR_INPUT
	TestName : T_MaxString;
END_VAR
""", """(* Compatibility entry: each admitted assertion already commits the canonical maximum.
The final result projector reads TestRecords directly; there is no history to calculate. *)
""")

helper("SetTestFailed", "", ["AssertionType : E_AssertionType", "AssertionMessage : T_MaxString"],
       ["_testIndex : UINT", "_execute : BOOL", "_result : ST_CoUnitComparisonResult"], """
IF NOT GVL_coUnit.coUnitRunner.ValidateContext(Suite := THIS, RequireTest := TRUE, TestIndex => _testIndex, Execute => _execute) THEN RETURN; END_IF
IF NOT _execute THEN RETURN; END_IF
_result.Passed := FALSE;
_result.ArgumentError := FALSE;
_result.ExpectedText := '';
_result.ActualText := '';
_result.DiagnosticSuffix := '';
RecordAssertionOutcome(TestIndex := _testIndex, Ordinal := TestRecords[_testIndex].InvocationOrdinal, AssertionType := AssertionType, Message := AssertionMessage, Comparison := _result);
""")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, text in FILES.items():
        if path.name.endswith(".IMP.exp"):
            assert not re.search(r"\b(?:AssertResults|AssertArrayResults|U_ExpectedOrActual|AlreadyReported)\b", text), path
            assert not re.search(r"\b(?:VAR|VAR_INPUT|VAR_OUTPUT|END_VAR)\b", text), path
    outcome = FILES[SUITE / "RecordAssertionOutcome/RecordAssertionOutcome.IMP.exp"]
    assert outcome.index("FirstFailure.IsSet := TRUE") > outcome.index("FirstFailure.ActualText :=")
    assert outcome.index("WRITE_DEVICE_LOG(") > outcome.index("FirstFailure.IsSet := TRUE")
    different = []
    for path, text in FILES.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                different.append(str(path.relative_to(HERE)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
    if different:
        raise SystemExit("Regeneration differs:\n" + "\n".join(different))
    print(f"{'Checked' if args.check else 'Generated'} {len(FILES)} sections; 44 public signatures and single-transaction wrappers verified.")


if __name__ == "__main__":
    main()
