# Tests in workshop actuator identification for front foils

the tests were concluded with faster sample rate of the adc and can_tx task 


``` git
brzan@DESKTOP-96QUNSQ MINGW64 /d/Dane/workspace/fore_board (master)
$ git diff
diff --git a/Core/Src/task_adc.c b/Core/Src/task_adc.c
index 80c61e1..3f6af9b 100644
--- a/Core/Src/task_adc.c
+++ b/Core/Src/task_adc.c
@@ -21,7 +21,7 @@ typedef enum {
        ADC_NUMBER_OF_CHANNELS,
 } ADC_channels_t;

-#define ADC_N_SAMPLES 16
+#define ADC_N_SAMPLES 10
 #define ADC_READY_FLAG 0x01

 /* Array for storing ADC results */
diff --git a/Core/Src/task_can_tx.c b/Core/Src/task_can_tx.c
index 79def4a..4f18cbd 100644
--- a/Core/Src/task_can_tx.c
+++ b/Core/Src/task_can_tx.c
@@ -70,8 +70,8 @@ static void send_actuator_right_foil_feedback(fore_board_t* fb_ptr)
 }

 static uint32_t distance_fore_feedback_message_period = 10; // centy seconds (10cs is 100ms)
-static uint32_t actuator_left_foil_feedback_message_period = 10;
-static uint32_t actuator_right_foil_feedback_message_period = 10;
+static uint32_t actuator_left_foil_feedback_message_period = 1;
+static uint32_t actuator_right_foil_feedback_message_period = 1;

 extern volatile uint32_t task_can_tx_alive;
 void task_can_tx(void *argument)

```
