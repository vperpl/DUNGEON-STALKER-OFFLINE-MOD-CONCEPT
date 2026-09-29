#include <Windows.h>
#include <stdio.h>
BOOL APIENTRY DllMain(HMODULE h, DWORD r, LPVOID p) {
    if (r == DLL_PROCESS_ATTACH) {
        FILE* f = NULL;
        if (!fopen_s(&f, "C:\\Users\\snipe\\Desktop\\DungeonStalkers_Bypass\\tools\\marker.txt", "a")) {
            fprintf(f, "LOADED pid\n"); fclose(f);
        }
    }
    return TRUE;
}
