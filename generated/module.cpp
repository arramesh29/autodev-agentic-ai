#include "module.h"
#include <iostream>

AEBSystem::AEBSystem() : sensorData(0.0), ttc(0.0) {}

void AEBSystem::acquireSensorData() {
    // Simulate sensor data acquisition
    sensorData = 100.0; // Example sensor data
}

double AEBSystem::calculateTTC() {
    // Simulate TTC calculation
    if (sensorData > 0) {
        ttc = sensorData / 30.0; // Example calculation
    }
    return ttc;
}

bool AEBSystem::checkCollisionWarning() {
    // Check if TTC is less than or equal to 1.5 seconds
    return ttc <= 1.5;
}

bool AEBSystem::initiateEmergencyBraking() {
    // Initiate braking if collision warning is true
    if (checkCollisionWarning()) {
        std::cout << "Emergency Braking Initiated!" << std::endl;
        return true;
    }
    return false;
}
