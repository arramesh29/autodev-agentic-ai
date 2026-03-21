#include "aeb_controller.h"
#include <gtest/gtest.h>

TEST(AEBControllerTest, ProcessSensorData_ValidConfidence) {
    AEBController aeb;
    EXPECT_TRUE(aeb.processSensorData(100.0, 20.0, 0.96));
}

TEST(AEBControllerTest, ProcessSensorData_InvalidConfidence) {
    AEBController aeb;
    EXPECT_FALSE(aeb.processSensorData(100.0, 20.0, 0.94));
}

TEST(AEBControllerTest, CalculateTTC_ZeroRelativeSpeed) {
    AEBController aeb;
    aeb.processSensorData(100.0, 0.0, 0.96);
    EXPECT_EQ(aeb.checkCollisionWarning(), false);
    EXPECT_EQ(aeb.applyEmergencyBrakes(), false);
}

TEST(AEBControllerTest, CheckCollisionWarning) {
    AEBController aeb;
    aeb.processSensorData(30.0, 20.0, 0.96);
    EXPECT_TRUE(aeb.checkCollisionWarning());
}

TEST(AEBControllerTest, ApplyEmergencyBrakes) {
    AEBController aeb;
    aeb.processSensorData(16.0, 20.0, 0.96);
    EXPECT_TRUE(aeb.applyEmergencyBrakes());
}

TEST(AEBControllerTest, NoCollisionWarning) {
    AEBController aeb;
    aeb.processSensorData(100.0, 20.0, 0.96);
    EXPECT_FALSE(aeb.checkCollisionWarning());
}

TEST(AEBControllerTest, NoEmergencyBrakes) {
    AEBController aeb;
    aeb.processSensorData(100.0, 20.0, 0.96);
    EXPECT_FALSE(aeb.applyEmergencyBrakes());
}
