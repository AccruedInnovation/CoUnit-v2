"""Generate test-only native CoUnit log observation objects; never calls CODESYS."""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1] if (HERE.parents[1] / 'docs').is_dir() else HERE.parents[4]
sys.path.insert(0, str(REPO / '_tools'))
import generate_plcopenxml as plc

objects = []
files = {}


def add(prefix, name, declaration, implementation=None, wrapper=False):
    item = plc.ObjectExport(prefix, name, declaration.strip(), implementation.strip() if implementation else None,
                            ('Qualification', 'LogCapture'), HERE / name)
    if not wrapper:
        objects.append(item)
    files[f'{prefix}.{name}.DEC.exp'] = declaration.strip() + '\n'
    if implementation is not None:
        files[f'{prefix}.{name}.IMP.exp'] = implementation.strip() + '\n'
    return item


add('GVL', 'GVL_QualificationLog', """
{attribute 'qualified_only'}
VAR_GLOBAL
	Active : BOOL;
	Registered : BOOL;
	EventHandle : SysTypes.RTS_IEC_HANDLE := SysTypes.RTS_INVALID_HANDLE;
	ComponentFilter : UDINT;
	Count : UINT;
	Entries : ARRAY[1..128] OF STRING(127);
	HexEntries : ARRAY[1..128] OF STRING(254);
	Bytes : ARRAY[1..128, 0..127] OF BYTE;
	Lengths : ARRAY[1..128] OF UINT;
	Classes : ARRAY[1..128] OF DINT;
	LastLogHandle : SysTypes.RTS_IEC_HANDLE;
	ObservedComponent : UDINT;
	Overflow : BOOL;
	Truncated : BOOL;
	CallbackErrors : UDINT;
	LastCopyError : SysTypes.RTS_IEC_RESULT;
	StartError : SysTypes.RTS_IEC_RESULT;
	UnregisterError : SysTypes.RTS_IEC_RESULT;
	CloseError : SysTypes.RTS_IEC_RESULT;
END_VAR
""")

add('POU', 'F_QualificationLogCallback', """
(* TEST ONLY: resolve event arguments through LogCopyInfo; never add a log entry. *)
FUNCTION F_QualificationLogCallback : SysTypes.RTS_IEC_RESULT
VAR_INPUT
	pEventParam : POINTER TO CmpEventMgr.EventParam;
END_VAR
VAR
	_event : POINTER TO CmpLog.EVTPARAM_CmpLogAdd;
	_source : POINTER TO BYTE;
	_dest : POINTER TO BYTE;
	_index : UINT;
	_i : UINT;
	_length : UINT;
	_resolved : STRING(127);
	_copyBytes : DINT;
	_copyResult : SysTypes.RTS_IEC_RESULT;
	_arguments : POINTER TO BYTE;
END_VAR
""", """
F_QualificationLogCallback := CmpErrors.Errors.ERR_OK;
IF NOT GVL_QualificationLog.Active THEN RETURN; END_IF
IF pEventParam = 0 THEN
	GVL_QualificationLog.CallbackErrors := GVL_QualificationLog.CallbackErrors + 1;
	RETURN;
END_IF
IF (pEventParam^.EventId <> CmpLog.EventIDs.EVT_LogAdd) OR
	(pEventParam^.CmpIdProvider <> CmpLog.EventIDs.CMPID_CmpLog) OR
	(pEventParam^.usParamId <> CmpLog.EventIDs.EVTPARAMID_CmpLogAdd) OR
	(pEventParam^.usVersion <> CmpLog.EventIDs.EVTVERSION_CmpLogAdd) THEN
	GVL_QualificationLog.CallbackErrors := GVL_QualificationLog.CallbackErrors + 1;
	RETURN;
END_IF
IF pEventParam^.pParameter = 0 THEN
	GVL_QualificationLog.CallbackErrors := GVL_QualificationLog.CallbackErrors + 1;
	RETURN;
END_IF
_event := pEventParam^.pParameter;
IF _event^.CmpId <> GVL_QualificationLog.ComponentFilter THEN RETURN; END_IF
IF _event^.pszInfo = 0 THEN
	GVL_QualificationLog.CallbackErrors := GVL_QualificationLog.CallbackErrors + 1;
	RETURN;
END_IF
IF GVL_QualificationLog.Count >= 128 THEN
	GVL_QualificationLog.Overflow := TRUE;
	RETURN;
END_IF
_index := GVL_QualificationLog.Count + 1;
(* LogAdd2's runtime event uses a format plus native argument list, not final pszInfo text.
   CmpLog >= 3.5.21 provides this ABI-owned resolver (CODESYS CDS-63087). *)
_copyBytes := SIZEOF(_resolved);
_arguments := _event^.pargList;
_copyResult := CmpLog.LogCopyInfo(hLogger := _event^.hLog, pszInfo := _event^.pszInfo,
	pargList := _arguments, pszString := ADR(_resolved), pdiMaxStringLen := ADR(_copyBytes));
IF _copyResult <> CmpErrors.Errors.ERR_OK THEN
	GVL_QualificationLog.LastCopyError := _copyResult;
	IF _copyResult = CmpErrors.Errors.ERR_BUFFERSIZE THEN GVL_QualificationLog.Truncated := TRUE;
	ELSE GVL_QualificationLog.CallbackErrors := GVL_QualificationLog.CallbackErrors + 1; END_IF
	RETURN;
END_IF
_source := ADR(_resolved);
_dest := ADR(GVL_QualificationLog.Entries[_index]);
_length := 0;
FOR _i := 0 TO 127 DO
	IF _source[_i] = 0 THEN EXIT; END_IF
	IF _i = 127 THEN GVL_QualificationLog.Truncated := TRUE; EXIT; END_IF
	_dest[_i] := _source[_i];
	GVL_QualificationLog.Bytes[_index, _i] := _source[_i];
	_length := _length + 1;
END_FOR
_dest[_length] := 0;
GVL_QualificationLog.Bytes[_index, _length] := 0;
GVL_QualificationLog.Lengths[_index] := _length;
GVL_QualificationLog.Classes[_index] := _event^.iClassID;
GVL_QualificationLog.LastLogHandle := _event^.hLog;
GVL_QualificationLog.ObservedComponent := _event^.CmpId;
(* Commit the record after its complete byte/text payload. Read after Stop succeeds. *)
GVL_QualificationLog.Count := _index;
""")

add('POU', 'F_QualificationLogStart', """
(* TEST ONLY: call before the fixture. Filter matches Support/CmpCfLog source. *)
FUNCTION F_QualificationLogStart : BOOL
VAR_INPUT
	ComponentFilter : UDINT := 16#11110000 OR ComponentID.CMPID_IecCode OR 16#0123;
END_VAR
VAR
	_result : SysTypes.RTS_IEC_RESULT;
END_VAR
""", """
IF GVL_QualificationLog.Registered OR (GVL_QualificationLog.EventHandle <> SysTypes.RTS_INVALID_HANDLE) THEN
	GVL_QualificationLog.StartError := 16#FFFF1001;
	RETURN;
END_IF
GVL_QualificationLog.Active := FALSE;
GVL_QualificationLog.Count := 0;
GVL_QualificationLog.Overflow := FALSE;
GVL_QualificationLog.Truncated := FALSE;
GVL_QualificationLog.CallbackErrors := 0;
GVL_QualificationLog.LastCopyError := CmpErrors.Errors.ERR_OK;
GVL_QualificationLog.StartError := CmpErrors.Errors.ERR_OK;
GVL_QualificationLog.UnregisterError := CmpErrors.Errors.ERR_OK;
GVL_QualificationLog.CloseError := CmpErrors.Errors.ERR_OK;
GVL_QualificationLog.ComponentFilter := ComponentFilter;
GVL_QualificationLog.ObservedComponent := 0;
GVL_QualificationLog.EventHandle := CmpEventMgr.EventOpen(Result := _result,
	EventId := DWORD_TO_UDINT(CmpLog.EventIDs.EVT_LogAdd),
	CmpIdProvider := DWORD_TO_UDINT(CmpLog.EventIDs.CMPID_CmpLog));
IF (_result <> CmpErrors.Errors.ERR_OK) OR (GVL_QualificationLog.EventHandle = SysTypes.RTS_INVALID_HANDLE) THEN
	GVL_QualificationLog.StartError := _result;
	IF _result = CmpErrors.Errors.ERR_OK THEN GVL_QualificationLog.StartError := 16#FFFF1002; END_IF
ELSE
	_result := CmpEventMgr.EventRegisterCallbackFunction(hEvent := GVL_QualificationLog.EventHandle,
		pfCallbackFunction := ADR(F_QualificationLogCallback));
	IF _result = CmpErrors.Errors.ERR_OK THEN
		GVL_QualificationLog.Registered := TRUE;
		GVL_QualificationLog.Active := TRUE;
		F_QualificationLogStart := TRUE;
		RETURN;
	END_IF
	GVL_QualificationLog.StartError := _result;
END_IF
(* Registration failed: release an opened event without losing close-failure evidence. *)
IF GVL_QualificationLog.EventHandle <> SysTypes.RTS_INVALID_HANDLE THEN
	GVL_QualificationLog.CloseError := CmpEventMgr.EventClose2(hEvent := GVL_QualificationLog.EventHandle);
	IF GVL_QualificationLog.CloseError = CmpErrors.Errors.ERR_OK THEN
		GVL_QualificationLog.EventHandle := SysTypes.RTS_INVALID_HANDLE;
	END_IF
END_IF
""")

add('POU', 'F_QualificationLogStop', """
(* TEST ONLY: unregister before closing; failed cleanup stays visible and retryable. *)
FUNCTION F_QualificationLogStop : BOOL
VAR
	_entry : UINT;
	_byteIndex : UINT;
	_digits : STRING(16) := '0123456789abcdef';
	_hex : POINTER TO BYTE;
	_dest : POINTER TO BYTE;
	_value : BYTE;
END_VAR
""", """
GVL_QualificationLog.Active := FALSE;
IF GVL_QualificationLog.Registered THEN
	GVL_QualificationLog.UnregisterError := CmpEventMgr.EventUnregisterCallbackFunction(
		hEvent := GVL_QualificationLog.EventHandle, pfCallbackFunction := ADR(F_QualificationLogCallback));
	IF GVL_QualificationLog.UnregisterError <> CmpErrors.Errors.ERR_OK THEN RETURN; END_IF
	GVL_QualificationLog.Registered := FALSE;
END_IF
(* Capture is now inactive and unregistered. Materialize ASCII hex for efficient host reads. *)
_hex := ADR(_digits);
FOR _entry := 1 TO GVL_QualificationLog.Count DO
	_dest := ADR(GVL_QualificationLog.HexEntries[_entry]);
	_byteIndex := 0;
	WHILE _byteIndex < GVL_QualificationLog.Lengths[_entry] DO
		_value := GVL_QualificationLog.Bytes[_entry, _byteIndex];
		_dest[2 * _byteIndex] := _hex[BYTE_TO_UINT(SHR(_value, 4))];
		_dest[2 * _byteIndex + 1] := _hex[BYTE_TO_UINT(_value AND BYTE#16#0F)];
		_byteIndex := _byteIndex + 1;
	END_WHILE
	_dest[2 * _byteIndex] := 0;
END_FOR
IF GVL_QualificationLog.EventHandle <> SysTypes.RTS_INVALID_HANDLE THEN
	GVL_QualificationLog.CloseError := CmpEventMgr.EventClose2(hEvent := GVL_QualificationLog.EventHandle);
	IF GVL_QualificationLog.CloseError <> CmpErrors.Errors.ERR_OK THEN RETURN; END_IF
	GVL_QualificationLog.EventHandle := SysTypes.RTS_INVALID_HANDLE;
END_IF
F_QualificationLogStop := TRUE;
""")

wrapper = add('POU', 'PRG_QualificationObserved', """
(* Optional wrapper: schedule this program instead of PRG_Qualification. *)
PROGRAM PRG_QualificationObserved
VAR_INPUT
	WaitForReport : BOOL := FALSE;
END_VAR
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	Started : BOOL;
	Stopped : BOOL;
	CaptureHealthy : BOOL;
	CapturedCount : UINT;
END_VAR
VAR
	_attempted : BOOL;
	_reportState : E_CoUnitReportState;
END_VAR
""", """
IF Done THEN RETURN; END_IF
IF NOT _attempted THEN
	_attempted := TRUE;
	Started := F_QualificationLogStart();
	IF NOT Started THEN
		Stopped := F_QualificationLogStop();
		Done := TRUE;
		RETURN;
	END_IF
END_IF
PRG_Qualification();
IF PRG_Qualification.Done THEN
	IF WaitForReport THEN
		_reportState := GVL_coUnit.coUnitRunner.xUnitXmlPublisher.GetReportState();
		IF (_reportState <> E_CoUnitReportState.WRITTEN) AND (_reportState <> E_CoUnitReportState.FAILED) AND
			(_reportState <> E_CoUnitReportState.DISABLED) THEN RETURN; END_IF
	END_IF
	Stopped := F_QualificationLogStop();
	CapturedCount := GVL_QualificationLog.Count;
	CaptureHealthy := Stopped AND NOT GVL_QualificationLog.Overflow AND NOT GVL_QualificationLog.Truncated AND
		(GVL_QualificationLog.CallbackErrors = 0) AND (GVL_QualificationLog.StartError = CmpErrors.Errors.ERR_OK) AND
		(GVL_QualificationLog.UnregisterError = CmpErrors.Errors.ERR_OK) AND (GVL_QualificationLog.CloseError = CmpErrors.Errors.ERR_OK);
	(* Content is independently verified from Bytes/Lengths; this is only execution/capture health. *)
	OraclePass := PRG_Qualification.OraclePass AND CaptureHealthy;
	Done := TRUE;
END_IF
""", wrapper=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    changed = []
    for name, text in files.items():
        path = HERE / name
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != text:
                changed.append(name)
        else:
            path.write_text(text, encoding='utf-8', newline='\n')
    if changed:
        raise SystemExit('Regeneration differs: ' + ', '.join(changed))
    if not args.check:
        plc.build_xml(objects, 'CoUnit native log event observer').write(str(HERE / 'observer.xml'), encoding='utf-8', xml_declaration=True)
        plc.build_xml([wrapper], 'CoUnit observed qualification wrapper').write(str(HERE / 'wrapper.xml'), encoding='utf-8', xml_declaration=True)
    print(f'{"Checked" if args.check else "Generated"} {len(files)} plaintext sections; observer.xml and optional wrapper.xml.')


if __name__ == '__main__':
    main()
