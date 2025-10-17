#include <fstream>
#include <iostream>

using namespace std;


int main() {
    fstream f("n.txt");
    string line;
    while (getline(f, line)) {
        cout << "0.0.0.0 " << line << '\n';
    }
}
