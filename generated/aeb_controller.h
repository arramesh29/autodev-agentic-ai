#ifndef AEB_CONTROLLER_H
#define AEB_CONTROLLER_H

class AEBController {
public:
    AEBController();
    bool processSensorData(double distance, double relativeSpeed, double confidenceLevel);
    bool checkCollisionWarning();
    bool applyEmergencyBrakes();

private:
    double calculateTTC(double distance, double relativeSpeed);
    double ttc;
    bool collisionWarning;
    bool emergencyBraking;
};

#endif // AEB_CONTROLLER_H
