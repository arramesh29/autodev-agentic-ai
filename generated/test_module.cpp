#include "module.h"
#include <cassert>

void testAcquireSensorData() {
    AEBSystem aeb;
    aeb.acquireSensorData();
    assert(aeb.calculateTTC() > 0);
}

void testCalculateTTC() {
    AEBSystem aeb;
    aeb.acquireSensorData();
    double ttc = aeb.calculateTTC();
    assert(ttc == 100.0 / 30.0);
}

void testCheckCollisionWarning() {
    AEBSystem aeb;
    aeb.acquireSensorData();
    aeb.calculateTTC();
    assert(aeb.checkCollisionWarning() == false);
}

void testInitiateEmergencyBraking() {
    AEBSystem aeb;
    aeb.acquireSensorData();
    aeb.calculateTTC();
    assert(aeb.initiateEmergencyBraking() == false);
}

int main() {
    testAcquireSensorData();
    testCalculateTTC();
    testCheckCollisionWarning();
    testInitiateEmergencyBraking();
    return 0;
}
