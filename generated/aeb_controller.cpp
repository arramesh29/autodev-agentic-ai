#include "aeb_controller.h"

AEBController::AEBController() : ttc(0.0), collisionWarning(false), emergencyBraking(false) {}

bool AEBController::processSensorData(double distance, double relativeSpeed, double confidenceLevel) {
    if (confidenceLevel < 0.95) {
        return false;
    }
    ttc = calculateTTC(distance, relativeSpeed);
    return true;
}

double AEBController::calculateTTC(double distance, double relativeSpeed) {
    if (relativeSpeed <= 0) {
        return std::numeric_limits<double>::infinity();
    }
    return distance / relativeSpeed;
}

bool AEBController::checkCollisionWarning() {
    collisionWarning = (ttc > 0 && ttc <= 1.5);
    return collisionWarning;
}

bool AEBController::applyEmergencyBrakes() {
    emergencyBraking = (ttc > 0 && ttc <= 0.8);
    return emergencyBraking;
}
