#include <Windows.h>
#include <iostream>
#include <chrono>
#include <fstream>
#include <string>
#include <cmath>
#include <cstdio>

#include "Generators/CppGenerator.h"
#include "Generators/MappingGenerator.h"
#include "Generators/IDAMappingGenerator.h"
#include "Generators/DumpspaceGenerator.h"

#include "Generators/Generator.h"
#include "Unreal/ObjectArray.h"

enum class EFortToastType : uint8
{
	Default                                  = 0,
	Subdued                                 = 1,
	Impactful                               = 2,
	Lock                                    = 3,
	EFortToastType_MAX                      = 4,
};

static const char* const WSLogPath = "C:\\Users\\snipe\\Desktop\\DungeonStalkers_Bypass\\tools\\inj.log";

static bool WSRead(const void* Addr, void* Out, size_t N)
{
	__try
	{
		memcpy(Out, Addr, N);
		return true;
	}
	__except (1)
	{
		return false;
	}
}

static bool WSPe(UEObject Obj, UEFunction Fn, void* Params)
{
	if (!Obj || !Fn)
		return false;

	__try
	{
		Obj.ProcessEvent(Fn, Params);
		return true;
	}
	__except (1)
	{
		return false;
	}
}

static bool WSLocation(void* Actor, double* Out)
{
	void* Root = nullptr;
	if (!WSRead((const uint8*)Actor + 0x1C0, &Root, 8) || !Root)
		return false;

	UEClass SceneCls = ObjectArray::FindClassFast("SceneComponent");
	UEFunction FLoc = SceneCls.GetFunction("SceneComponent", "K2_GetComponentToWorld");
	if (!FLoc)
		return false;

	uint8 Params[0x60] = {};
	if (!WSPe(UEObject(Root), FLoc, Params))
		return false;

	double* T = reinterpret_cast<double*>(Params + 0x20);
	Out[0] = T[0]; Out[1] = T[1]; Out[2] = T[2];
	return true;
}

static void WSLogLoc(std::ofstream& Log, const char* Tag, void* Actor)
{
	double L[3] = {};
	if (WSLocation(Actor, L))
		Log << "  " << Tag << " loc=(" << L[0] << "," << L[1] << "," << L[2] << ")\n";
	else
		Log << "  " << Tag << " loc=FAIL\n";
	Log.flush();
}

static void WSAddMove(void* Pawn, double DirX, double DirY, double DirZ, int Count, int DelayMs)
{
	UEClass PawnCls = ObjectArray::FindClassFast("Pawn");
	UEFunction FAdd = PawnCls.GetFunction("Pawn", "AddMovementInput");
	if (!FAdd)
		return;

	struct { double X, Y, Z; float Scale; uint8 Force; uint8 Pad[3]; } P{};
	P.X = DirX; P.Y = DirY; P.Z = DirZ; P.Scale = 1.0f;

	for (int i = 0; i < Count; ++i)
	{
		WSPe(UEObject(Pawn), FAdd, &P);
		Sleep(DelayMs);
	}
}

static const char* const WSMapFilePath = "C:\\Users\\snipe\\Desktop\\DungeonStalkers_Bypass\\tools\\map.txt";
static const char* const WSFixFlagPath = "C:\\Users\\snipe\\Desktop\\DungeonStalkers_Bypass\\tools\\fix.txt";

static void WSAppendLog(const std::string& Text)
{
	HANDLE H = CreateFileA(WSLogPath, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
	if (H == INVALID_HANDLE_VALUE)
		return;

	DWORD Written = 0;
	SetFilePointer(H, 0, nullptr, FILE_END);
	WriteFile(H, Text.data(), static_cast<DWORD>(Text.size()), &Written, nullptr);
	CloseHandle(H);
}

static void WSAppendLogC(const char* Text)
{
	HANDLE H = CreateFileA(WSLogPath, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
	if (H == INVALID_HANDLE_VALUE)
		return;

	DWORD Written = 0;
	SetFilePointer(H, 0, nullptr, FILE_END);
	WriteFile(H, Text, static_cast<DWORD>(strlen(Text)), &Written, nullptr);
	CloseHandle(H);
}

static bool WSFindLocal(void** OutCtrl, void** OutGI)
{
	*OutCtrl = nullptr;
	*OutGI = nullptr;

	UEClass CtrlCls = ObjectArray::FindClassFast("PlayerController");
	const int32 Total = ObjectArray::Num();
	void* Ctrl = nullptr;
	void* GI = nullptr;

	for (int32 i = 0; i < Total; ++i)
	{
		UEObject O = ObjectArray::GetByIndex(i);
		if (!O)
			continue;

		if (!GI)
		{
			const std::string ClsName = O.GetClass().GetName();
			if ((ClsName == "BP_WSGameInstance_C" || ClsName == "WSGameInstance") && O.GetName().rfind("Default__", 0) != 0)
				GI = O.GetAddress();
		}

		if (!Ctrl && O.IsA(CtrlCls) && O.GetName().rfind("Default__", 0) != 0)
		{
			void* Player = nullptr;
			if (WSRead((const uint8*)O.GetAddress() + 0x350, &Player, 8) && Player)
				Ctrl = O.GetAddress();
		}

		if (Ctrl && GI)
			break;
	}

	*OutCtrl = Ctrl;
	*OutGI = GI;
	return Ctrl != nullptr;
}

static bool WSReadMapFile(std::string& Out)
{
	std::ifstream F(WSMapFilePath);
	if (!F)
		return false;

	if (!std::getline(F, Out))
		return false;

	while (!Out.empty() && (Out.back() == '\r' || Out.back() == '\n' || Out.back() == ' ' || Out.back() == '\t'))
		Out.pop_back();

	return !Out.empty();
}

static void WSOpenMap()
{
	std::string Map;
	if (!WSReadMapFile(Map))
	{
		WSAppendLog("[F8] map.txt missing or empty\n");
		return;
	}

	void* Ctrl = nullptr;
	void* GI = nullptr;
	if (!WSFindLocal(&Ctrl, &GI))
	{
		WSAppendLog("[F8] no local player controller found\n");
		return;
	}

	UEClass Kismet = ObjectArray::FindClassFast("KismetSystemLibrary");
	UEFunction FExec = Kismet.GetFunction("KismetSystemLibrary", "ExecuteConsoleCommand");
	if (!FExec)
	{
		WSAppendLog("[F8] ExecuteConsoleCommand MISSING\n");
		return;
	}

	static wchar_t CmdBuf[768];
	const size_t N = Map.size() < 700 ? Map.size() : 700;
	for (size_t i = 0; i < N; ++i)
		CmdBuf[i] = static_cast<wchar_t>(static_cast<unsigned char>(Map[i]));
	CmdBuf[N] = L'\0';

	std::wstring Cmd = L"open ";
	Cmd += CmdBuf;

	static wchar_t CmdStore[768];
	for (size_t i = 0; i < Cmd.size() && i < 767; ++i)
		CmdStore[i] = Cmd[i];
	CmdStore[Cmd.size() < 767 ? Cmd.size() : 767] = L'\0';

	struct
	{
		void* WorldContextObject;
		void* CommandData;
		int32 CommandNum;
		int32 CommandMax;
		void* SpecificPlayer;
	} P{};
	P.WorldContextObject = GI;
	P.CommandData = CmdStore;
	P.CommandNum = static_cast<int32>(wcslen(CmdStore) + 1);
	P.CommandMax = P.CommandNum;
	P.SpecificPlayer = Ctrl;

	std::string Msg = "[F8] cmd='";
	Msg += Map;
	Msg += "' gi=0x";
	{
		char B[32];
		sprintf_s(B, "%llx", reinterpret_cast<unsigned long long>(GI));
		Msg += B;
	}
	Msg += " ctrl=0x";
	{
		char B[32];
		sprintf_s(B, "%llx", reinterpret_cast<unsigned long long>(Ctrl));
		Msg += B;
	}
	Msg += " -> ";
	Msg += WSPe(UEObject(Ctrl), FExec, &P) ? "dispatched\n" : "FAILED\n";
	WSAppendLog(Msg);
}

static void WSOpenMapSafe()
{
	__try
	{
		WSOpenMap();
	}
	__except (1)
	{
		WSAppendLogC("[F8] !!! ExecuteConsoleCommand raised an SEH exception !!!\n");
	}
}

static bool WSObjAlive(void* P)
{
	if (!P)
		return false;

	void* Cls = nullptr;
	return WSRead((const uint8*)P, &Cls, 8) && Cls;
}

static bool WSWrite(const void* Src, void* Dst, size_t N)
{
	__try
	{
		memcpy(Dst, Src, N);
		return true;
	}
	__except (1)
	{
		return false;
	}
}

static bool g_DrvOn = true;
static void* g_DrvCtrl = nullptr;
static void* g_DrvPawn = nullptr;
static ULONGLONG g_DrvLastScan = 0;
static bool g_DrvJumpEdge = false;
static bool g_DrvEngaged = false;
static void* g_DrvCM = nullptr;
static float g_DrvSpeed = 400.0f;

static void WSDrvRefresh()
{
	if (WSObjAlive(g_DrvCtrl) && WSObjAlive(g_DrvPawn))
		return;

	const ULONGLONG Now = GetTickCount64();
	if (Now - g_DrvLastScan < 3000)
		return;
	g_DrvLastScan = Now;
	g_DrvEngaged = false;

	g_DrvCtrl = nullptr;
	g_DrvPawn = nullptr;

	void* GI = nullptr;
	if (!WSFindLocal(&g_DrvCtrl, &GI) || !g_DrvCtrl)
	{
		WSAppendLog("[drv] no local controller\n");
		return;
	}

	WSRead((const uint8*)g_DrvCtrl + 0x300, &g_DrvPawn, 8);
	if (!WSObjAlive(g_DrvPawn))
	{
		void* P = nullptr;
		WSRead((const uint8*)g_DrvCtrl + 0x2F0, &P, 8);
		g_DrvPawn = WSObjAlive(P) ? P : nullptr;
	}

	WSAppendLog(g_DrvPawn ? "[drv] ctrl+character acquired\n" : "[drv] ctrl found, no character\n");
}

static bool WSGameFocused()
{
	HWND FG = GetForegroundWindow();
	if (!FG)
		return false;

	DWORD Pid = 0;
	GetWindowThreadProcessId(FG, &Pid);
	return Pid == GetCurrentProcessId();
}

static void WSInputTick()
{
	if (GetAsyncKeyState(VK_F1) & 1)
	{
		g_DrvOn = !g_DrvOn;
		WSAppendLog(g_DrvOn ? "[drv] ENABLED\n" : "[drv] disabled\n");
	}

	if (!g_DrvOn || !WSGameFocused())
		return;

	WSDrvRefresh();
	if (!g_DrvCtrl || !g_DrvPawn)
		return;

	uint8 Flags = 0;
	if (!WSRead((const uint8*)g_DrvCtrl + 0x554, &Flags, 1))
		return;
	if (Flags & 1)
		return;

	if (!g_DrvEngaged)
	{
		g_DrvEngaged = true;

		UEClass CtrlCls = ObjectArray::FindClassFast("Controller");
		UEFunction FResetMove = CtrlCls.GetFunction("Controller", "ResetIgnoreMoveInput");
		UEFunction FResetLook = CtrlCls.GetFunction("Controller", "ResetIgnoreLookInput");
		uint8 NoParams[8] = {};
		if (FResetMove)
			WSPe(UEObject(g_DrvCtrl), FResetMove, NoParams);
		if (FResetLook)
			WSPe(UEObject(g_DrvCtrl), FResetLook, NoParams);

		void* CM = nullptr;
		WSRead((const uint8*)g_DrvPawn + 0x338, &CM, 8);

		char Buf[320];
		uint8 MMode = 0;
		float MaxWS = 0.0f, Accel = 0.0f;
		double Vel[3] = {};
		WSRead((const uint8*)CM + 0x221, &MMode, 1);
		WSRead((const uint8*)CM + 0x268, &MaxWS, 4);
		WSRead((const uint8*)CM + 0x27C, &Accel, 4);
		WSRead((const uint8*)CM + 0xB8, Vel, 24);

		const int N = snprintf(Buf, sizeof(Buf),
			"[drv] engaged cm=0x%llX mode=%d maxWS=%.1f accel=%.1f vel=(%.1f,%.1f,%.1f)\n",
			(unsigned long long)(uintptr_t)CM, (int)MMode, MaxWS, Accel, Vel[0], Vel[1], Vel[2]);
		if (N > 0)
			WSAppendLogC(Buf);

		g_DrvCM = CM;
		g_DrvSpeed = (MaxWS > 50.0f) ? MaxWS : 400.0f;
	}

	const double Deg = 3.14159265358979323846 / 180.0;
	double Rot[3] = {};
	if (!WSRead((const uint8*)g_DrvCtrl + 0x328, Rot, 24))
		return;

	// --- mouse look ---
	{
		RECT R;
		if (GetClientRect(GetForegroundWindow(), &R))
		{
			POINT C = { (R.right - R.left) / 2, (R.bottom - R.top) / 2 };
			ClientToScreen(GetForegroundWindow(), &C);

			POINT P = {};
			if (GetCursorPos(&P))
			{
				const int DX = P.x - C.x;
				const int DY = P.y - C.y;
				if (DX != 0 || DY != 0)
				{
					SetCursorPos(C.x, C.y);
					Rot[1] += DX * 0.06;
					Rot[0] -= DY * 0.06;
					if (Rot[0] > 89.0) Rot[0] = 89.0;
					if (Rot[0] < -89.0) Rot[0] = -89.0;
					if (Rot[1] > 180.0) Rot[1] -= 360.0;
					if (Rot[1] < -180.0) Rot[1] += 360.0;
					WSWrite(Rot, (uint8*)g_DrvCtrl + 0x328, 24);
				}
			}
		}
	}

	// --- WASD -> ControlInputVector ---
	const double Y = Rot[1] * Deg;
	const double FX = std::cos(Y), FY = std::sin(Y);
	const double RX = -std::sin(Y), RY = std::cos(Y);

	double MX = 0.0, MY = 0.0;
	if (GetAsyncKeyState('W') & 0x8000) { MX += FX; MY += FY; }
	if (GetAsyncKeyState('S') & 0x8000) { MX -= FX; MY -= FY; }
	if (GetAsyncKeyState('D') & 0x8000) { MX += RX; MY += RY; }
	if (GetAsyncKeyState('A') & 0x8000) { MX -= RX; MY -= RY; }

	double In[3] = { 0.0, 0.0, 0.0 };
	if (MX != 0.0 || MY != 0.0)
	{
		const double Len = std::sqrt(MX * MX + MY * MY);
		In[0] = MX / Len;
		In[1] = MY / Len;
	}
	WSWrite(In, (uint8*)g_DrvPawn + 0x2F8, 24);

	if (g_DrvCM && WSObjAlive(g_DrvCM) && (In[0] != 0.0 || In[1] != 0.0))
	{
		float MaxWS = g_DrvSpeed;
		WSRead((const uint8*)g_DrvCM + 0x268, &MaxWS, 4);
		if (MaxWS <= 50.0f)
			MaxWS = g_DrvSpeed;

		double Vel[2] = { In[0] * MaxWS, In[1] * MaxWS };
		WSWrite(Vel, (uint8*)g_DrvCM + 0xB8, 16);
	}

	// --- jump ---
	const bool bJump = (GetAsyncKeyState(VK_SPACE) & 0x8000) != 0;
	if (bJump && !g_DrvJumpEdge)
	{
		UEClass ChCls = ObjectArray::FindClassFast("Character");
		UEFunction FJump = ChCls.GetFunction("Character", "Jump");
		if (FJump)
		{
			uint8 NoParams[8] = {};
			WSPe(UEObject(g_DrvPawn), FJump, NoParams);
		}
	}
	g_DrvJumpEdge = bJump;
}

static void WSRun()
{
	std::ofstream Log(WSLogPath, std::ios::app);
	if (!Log)
		return;

	Log << std::boolalpha;
	Log << "=== WSRun begin ===\n";
	Log.flush();

	const int32 Total = ObjectArray::Num();
	Log << "objects=" << Total << "\n";

	{
		UEClass WorldCls = ObjectArray::FindClassFast("World");
		int Logged = 0;
		for (int32 i = 0; i < Total && Logged < 4; ++i)
		{
			UEObject O = ObjectArray::GetByIndex(i);
			if (!O || !O.IsA(WorldCls) || O.GetName().rfind("Default__", 0) == 0)
				continue;
			Log << "world     = " << O.GetFullName() << "\n";
			++Logged;
		}
		if (!Logged)
			Log << "world     = NONE\n";

		UEClass GSCls = ObjectArray::FindClassFast("GameStateBase");
		for (int32 i = 0; i < Total; ++i)
		{
			UEObject O = ObjectArray::GetByIndex(i);
			if (!O || !O.IsA(GSCls) || O.GetName().rfind("Default__", 0) == 0)
				continue;

			void* GMode = nullptr;
			void* AMode = nullptr;
			WSRead((const uint8*)O.GetAddress() + 0x2B0, &GMode, 8);
			WSRead((const uint8*)O.GetAddress() + 0x2B8, &AMode, 8);

			Log << "gamestate = " << O.GetFullName() << "\n";
			Log << "  GameModeClass=" << (GMode ? UEObject(GMode).GetName() : std::string("null")) << "\n";
			Log << "  AuthorityGameMode=" << (AMode ? UEObject(AMode).GetName() : std::string("null")) << "\n";
			break;
		}
	}

	UEClass CtrlCls = ObjectArray::FindClassFast("PlayerController");
	UEObject Ctrl;

	for (int32 i = 0; i < Total; ++i)
	{
		UEObject O = ObjectArray::GetByIndex(i);
		if (!O || !O.IsA(CtrlCls))
			continue;

		const std::string Nm = O.GetName();
		if (Nm.rfind("Default__", 0) == 0)
			continue;

		void* Player = nullptr;
		if (!WSRead((const uint8*)O.GetAddress() + 0x350, &Player, 8) || !Player)
			continue;

		Ctrl = O;
		break;
	}

	if (!Ctrl)
	{
		Log << "no local player controller found\n";
		Log.flush();
		return;
	}

	uint8* C = reinterpret_cast<uint8*>(Ctrl.GetAddress());

	void* Pawn = nullptr;
	void* HUD = nullptr;
	void* PlayerInput = nullptr;
	WSRead(C + 0x2F0, &Pawn, 8);
	WSRead(C + 0x360, &HUD, 8);
	WSRead(C + 0x428, &PlayerInput, 8);

	Log << "ctrl      = 0x" << std::hex << reinterpret_cast<uintptr_t>(C) << std::dec << "  class=" << Ctrl.GetClass().GetName() << "\n";
	Log << "name      = " << Ctrl.GetFullName() << "\n";
	Log << "pawn      = 0x" << std::hex << reinterpret_cast<uintptr_t>(Pawn) << std::dec << "\n";
	Log << "hud       = 0x" << std::hex << reinterpret_cast<uintptr_t>(HUD) << std::dec << "\n";
	Log << "playerinp = 0x" << std::hex << reinterpret_cast<uintptr_t>(PlayerInput) << std::dec << "\n";

	void* Cam = nullptr;
	WSRead(C + 0x368, &Cam, 8);
	Log << "camera    = 0x" << std::hex << reinterpret_cast<uintptr_t>(Cam) << std::dec << "\n";
	if (Pawn)
		Log << "pawnfull  = " << UEObject(Pawn).GetFullName() << "\n";
	else
		Log << "pawnfull  = NONE\n";
	Log << "ctrlouter = " << (Ctrl.GetOuter() ? Ctrl.GetOuter().GetFullName() : std::string("null")) << "\n";

	UEObject GameInst;
	for (int32 i = 0; i < Total; ++i)
	{
		UEObject O = ObjectArray::GetByIndex(i);
		if (!O || O.GetName().rfind("Default__", 0) == 0)
			continue;
		UEClass Cls = O.GetClass();
		if (Cls.GetName() == "BP_WSGameInstance_C" || Cls.GetName() == "WSGameInstance")
		{
			GameInst = O;
			break;
		}
	}
	Log << "gameinst  = 0x" << std::hex << reinterpret_cast<uintptr_t>(GameInst.GetAddress()) << std::dec
		<< "  class=" << GameInst.GetClass().GetName() << "\n";

	uint8 B340 = 0, B554 = 0, B4C0 = 0, B620 = 0;
	WSRead(C + 0x340, &B340, 1);
	WSRead(C + 0x554, &B554, 1);
	WSRead(C + 0x4C0, &B4C0, 1);
	WSRead(C + 0x620, &B620, 1);
	Log << std::hex;
	Log << "ctrl+0x340=" << (int)B340 << "  ctrl+0x4C0=" << (int)B4C0 << "  ctrl+0x554=" << (int)B554 << "  ctrl+0x620=" << (int)B620 << "\n";
	Log << std::dec;

	void* InactiveIC = nullptr;
	WSRead(C + 0x618, &InactiveIC, 8);
	Log << "inactiveInputComp=0x" << std::hex << reinterpret_cast<uintptr_t>(InactiveIC) << std::dec << "\n";
	Log.flush();

	double CRot[3] = {};
	WSRead(C + 0x328, CRot, 24);
	const double Deg = 3.14159265358979323846 / 180.0;
	const double P = CRot[0] * Deg;
	const double Y = CRot[1] * Deg;
	const double DirX = std::cos(P) * std::cos(Y);
	const double DirY = std::cos(P) * std::sin(Y);
	const double DirZ = -std::sin(P);
	Log << "controlRot=(" << CRot[0] << "," << CRot[1] << "," << CRot[2] << ")\n";
	Log.flush();

	const DWORD AttrA = GetFileAttributesA(WSFixFlagPath);
	bool bDoFix = (AttrA != INVALID_FILE_ATTRIBUTES);
	Log << "fixflag=0x" << std::hex << AttrA << " lasterr=" << GetLastError() << std::dec << "\n";
	if (bDoFix)
	{
		std::ifstream FixFile(WSFixFlagPath);
		bDoFix = FixFile.good();
	}

	if (Pawn && bDoFix)
	{
		Log << "-- phase A: raw AddMovementInput, no fixes --\n";
		Log.flush();
		WSLogLoc(Log, "before", Pawn);
		WSAddMove(Pawn, DirX, DirY, DirZ, 30, 50);
		WSLogLoc(Log, "afterA", Pawn);
	}

	if (bDoFix)
	{
		Log << "-- phase B: apply fixes --\n";
	}
	else
	{
		Log << "-- phase B SKIPPED (no fix.txt) --\n";
	}
	Log.flush();

	if (bDoFix)
	{
	UEClass ControllerCls = ObjectArray::FindClassFast("Controller");
	UEFunction FResetMove = ControllerCls.GetFunction("Controller", "ResetIgnoreMoveInput");
	UEFunction FResetLook = ControllerCls.GetFunction("Controller", "ResetIgnoreLookInput");
	UEFunction FSetMove = ControllerCls.GetFunction("Controller", "SetIgnoreMoveInput");
	UEFunction FSetLook = ControllerCls.GetFunction("Controller", "SetIgnoreLookInput");
	Log << "ResetIgnoreMoveInput=" << (FResetMove ? "OK" : "MISSING")
		<< " ResetIgnoreLookInput=" << (FResetLook ? "OK" : "MISSING")
		<< " SetIgnoreMoveInput=" << (FSetMove ? "OK" : "MISSING")
		<< " SetIgnoreLookInput=" << (FSetLook ? "OK" : "MISSING") << "\n";

	uint8 NoParams[8] = {};
	Log << "call ResetIgnoreMoveInput=" << WSPe(Ctrl, FResetMove, NoParams) << "\n";
	memset(NoParams, 0, sizeof(NoParams));
	Log << "call ResetIgnoreLookInput=" << WSPe(Ctrl, FResetLook, NoParams) << "\n";

	uint8 BoolParam[8] = { 0,0,0,0,0,0,0,0 };
	WSPe(Ctrl, FSetMove, BoolParam);
	memset(BoolParam, 0, sizeof(BoolParam));
	WSPe(Ctrl, FSetLook, BoolParam);
	Log.flush();

	if (GameInst)
	{
		UEClass GICls = ObjectArray::FindClassFast("WSGameInstance");
		UEFunction FSetState = GICls.GetFunction("WSGameInstance", "SetGameStateType");
		Log << "SetGameStateType=" << (FSetState ? "OK" : "MISSING") << "\n";
		uint8 State[8] = {};
		State[0] = 3; // EGameState::Tutorial
		Log << "call SetGameStateType(3)=" << WSPe(GameInst, FSetState, State) << "\n";
	}

	{
		UEClass WSICCls = ObjectArray::FindClassFast("WSPlayerController");
		UEFunction FMatch = WSICCls.GetFunction("WSPlayerController", "SetMatchHasStarted");
		UEFunction FUpdChar = WSICCls.GetFunction("WSPlayerController", "UpdateCharacter");
		UEFunction FUpdWid = WSICCls.GetFunction("WSPlayerController", "UpdateGameWidget");
		Log << "SetMatchHasStarted=" << (FMatch ? "OK" : "MISSING")
			<< " UpdateCharacter=" << (FUpdChar ? "OK" : "MISSING")
			<< " UpdateGameWidget=" << (FUpdWid ? "OK" : "MISSING") << "\n";

		uint8 Started[8] = { 1,0,0,0,0,0,0,0 };
		Log << "call SetMatchHasStarted(true)=" << WSPe(Ctrl, FMatch, Started) << "\n";

		if (Pawn)
		{
			UEObject PawnObj(Pawn);
			if (PawnObj.IsA(ObjectArray::FindClassFast("WSCharacterPlayer")))
			{
				uint8 Chars[8] = {};
				memcpy(Chars, &Pawn, 8);
				Log << "call UpdateCharacter(pawn)=" << WSPe(Ctrl, FUpdChar, Chars) << "\n";
			}
			else
			{
				Log << "pawn is not WSCharacterPlayer, class=" << PawnObj.GetClass().GetName() << "\n";
			}
		}

		uint8 WidParams[8] = {};
		Log << "call UpdateGameWidget=" << WSPe(Ctrl, FUpdWid, WidParams) << "\n";
	}

	{
		UEObject Subsystem;
		UEObject IMC;
		for (int32 i = 0; i < Total; ++i)
		{
			UEObject O = ObjectArray::GetByIndex(i);
			if (!O)
				continue;

			const std::string ClsName = O.GetClass().GetName();
			if (ClsName == "EnhancedInputLocalPlayerSubsystem" && O.GetName().rfind("Default__", 0) != 0)
				Subsystem = O;
			if (ClsName == "InputMappingContext" && O.GetName() == "IMC_InGame")
				IMC = O;
		}

		Log << "inputSubsystem=0x" << std::hex << reinterpret_cast<uintptr_t>(Subsystem.GetAddress()) << std::dec << "\n";
		Log << "IMC_InGame=0x" << std::hex << reinterpret_cast<uintptr_t>(IMC.GetAddress()) << std::dec << "\n";

		if (Subsystem && IMC)
		{
			UEClass IfaceCls = ObjectArray::FindClassFast("EnhancedInputSubsystemInterface");
			UEFunction FRem = IfaceCls.GetFunction("EnhancedInputSubsystemInterface", "RemoveMappingContext");
			UEFunction FAdd = IfaceCls.GetFunction("EnhancedInputSubsystemInterface", "AddMappingContext");
			Log << "RemoveMappingContext=" << (FRem ? "OK" : "MISSING")
				<< " AddMappingContext=" << (FAdd ? "OK" : "MISSING") << "\n";

			if (FRem)
			{
				struct { void* Mc; uint8 Opt; uint8 Pad[7]; } RP = { IMC.GetAddress(), 0 };
				Log << "call RemoveMappingContext=" << WSPe(Subsystem, FRem, &RP) << "\n";
			}
			if (FAdd)
			{
				struct { void* Mc; int32 Pri; uint8 Opt; uint8 Pad[3]; } AP = { IMC.GetAddress(), 0, 0 };
				Log << "call AddMappingContext(0)=" << WSPe(Subsystem, FAdd, &AP) << "\n";
			}
		}
	}
	Log.flush();
	} // end if(bDoFix)

	B340 = 0; B554 = 0;
	WSRead(C + 0x340, &B340, 1);
	WSRead(C + 0x554, &B554, 1);
	Log << std::hex << "after: ctrl+0x340=" << (int)B340 << "  ctrl+0x554=" << (int)B554 << std::dec << "\n";
	Log.flush();

	if (Pawn)
	{
		Log << "-- phase C: AddMovementInput after fixes --\n";
		Log.flush();
		WSAddMove(Pawn, DirX, DirY, DirZ, 30, 50);
		WSLogLoc(Log, "afterC", Pawn);
	}

	Log << "=== WSRun done ===\n";
	Log.flush();
}

static void WSRunSafe()
{
	__try
	{
		WSRun();
	}
	__except (1)
	{
		const char Msg[] = "!!! WSRun raised an SEH exception !!!\n";
		HANDLE H = CreateFileA(WSLogPath, FILE_APPEND_DATA, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
		if (H != INVALID_HANDLE_VALUE)
		{
			DWORD Written = 0;
			SetFilePointer(H, 0, nullptr, FILE_END);
			WriteFile(H, Msg, sizeof(Msg) - 1, &Written, nullptr);
			CloseHandle(H);
		}
	}
}

DWORD MainThread(HMODULE Module)
{
	AllocConsole();
	HWND ConsoleWnd = GetConsoleWindow();
	if (ConsoleWnd)
	{
		ShowWindow(ConsoleWnd, SW_HIDE);
		SetWindowPos(ConsoleWnd, HWND_BOTTOM, -32000, -32000, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);
	}

	FILE* Dummy;
	freopen_s(&Dummy, "CONIN$", "r", stdin);
	freopen_s(&Dummy, "CONOUT$", "w", stderr);
	std::cerr.clear();
	std::cerr << std::boolalpha << std::hex;

	std::cerr << "Initializing [Dumper-7]\n";

	Settings::Config::Load();
	Settings::Config::DelayDumperStart();

	std::cerr << "Started Generation [Dumper-7]!\n";
	auto DumpStartTime = std::chrono::high_resolution_clock::now();

	Generator::InitEngineCore();
	Generator::InitInternal();

	if (Settings::Generator::GameName.empty() && Settings::Generator::GameVersion.empty())
	{
		FString Name;
		FString Version;
		UEClass Kismet = ObjectArray::FindClassFast("KismetSystemLibrary");
		UEFunction GetGameName = Kismet.GetFunction("KismetSystemLibrary", "GetGameName");
		UEFunction GetEngineVersion = Kismet.GetFunction("KismetSystemLibrary", "GetEngineVersion");

		Kismet.ProcessEvent(GetGameName, &Name);
		Kismet.ProcessEvent(GetEngineVersion, &Version);

		Settings::Generator::GameName = Name.ToString();
		Settings::Generator::GameVersion = Version.ToString();
	}

	std::cerr << "GameName: " << Settings::Generator::GameName << "\n";
	std::cerr << "GameVersion: " << Settings::Generator::GameVersion << "\n\n";

	std::cerr << "FolderName: " << (Settings::Generator::GameVersion + '-' + Settings::Generator::GameName) << "\n\n";

	Generator::Generate<CppGenerator>();
	Generator::Generate<MappingGenerator>();
	Generator::Generate<IDAMappingGenerator>();
	Generator::Generate<DumpspaceGenerator>();

	auto DumpFinishTime = std::chrono::high_resolution_clock::now();

	std::chrono::duration<double, std::milli> DumpTime = DumpFinishTime - DumpStartTime;

	std::cerr << "\n\nGenerating SDK took (" << DumpTime.count() << "ms)\n\n\n";

	{
		std::ofstream Fresh(WSLogPath, std::ios::trunc);
	}

	WSRunSafe();

	if (Settings::Debug::bExecuteSDKTestScript)
	{
		CppGenerator::ExecuteSDKCompilationTestScript();
	}

	std::cerr << "\n\nF1=driver on/off  F6=unload  F8=open map.txt  F9=diagnostics\nWASD=move  mouse=look  Space=jump\n\n\n";

	while (true)
	{
		WSInputTick();

		if (GetAsyncKeyState(VK_F8) & 1)
		{
			g_DrvCtrl = nullptr;
			g_DrvPawn = nullptr;
			WSOpenMapSafe();
		}

		if (GetAsyncKeyState(VK_F9) & 1)
		{
			WSRunSafe();
		}

		if (GetAsyncKeyState(VK_F6) & 1)
		{
			fclose(stderr);
			if (Dummy)
			{
				fclose(Dummy);
			}
			FreeConsole();

			FreeLibraryAndExitThread(Module, 0);
		}

		Sleep(16);
	}

	return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved)
{
	switch (reason)
	{
	case DLL_PROCESS_ATTACH:
		CreateThread(0, 0, (LPTHREAD_START_ROUTINE)MainThread, hModule, 0, 0);
		break;
	}

	return TRUE;
}
