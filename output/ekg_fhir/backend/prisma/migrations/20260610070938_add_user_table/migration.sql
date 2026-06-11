-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('PATIENT', 'NAKES', 'ADMIN');

-- CreateTable
CREATE TABLE "users" (
    "user_id" UUID NOT NULL,
    "full_name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "gender" VARCHAR(20) NOT NULL,
    "phone_number" VARCHAR(20) NOT NULL,
    "password" VARCHAR(255) NOT NULL,
    "role" "UserRole" NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "users_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "patients" (
    "patient_id" UUID NOT NULL,
    "user_id" UUID,
    "full_name" VARCHAR(255) NOT NULL,
    "medical_record_number" VARCHAR(100) NOT NULL,
    "gender" VARCHAR(20) NOT NULL,
    "birth_date" DATE NOT NULL,
    "height_cm" DOUBLE PRECISION,
    "weight_kg" DOUBLE PRECISION,

    CONSTRAINT "patients_pkey" PRIMARY KEY ("patient_id")
);

-- CreateTable
CREATE TABLE "devices" (
    "device_id" UUID NOT NULL,
    "device_name" VARCHAR(255) NOT NULL,
    "serial_number" VARCHAR(100) NOT NULL,

    CONSTRAINT "devices_pkey" PRIMARY KEY ("device_id")
);

-- CreateTable
CREATE TABLE "ecg_sessions" (
    "session_id" UUID NOT NULL,
    "patient_id" UUID NOT NULL,
    "device_id" UUID NOT NULL,
    "created_by" UUID,
    "examination_time" TIMESTAMP(3) NOT NULL,
    "duration_sec" INTEGER NOT NULL,
    "lead_configuration" VARCHAR(100) NOT NULL,
    "status" VARCHAR(50) NOT NULL,
    "source_type" VARCHAR(50) NOT NULL,

    CONSTRAINT "ecg_sessions_pkey" PRIMARY KEY ("session_id")
);

-- CreateTable
CREATE TABLE "ecg_signal_data" (
    "signal_id" BIGSERIAL NOT NULL,
    "session_id" UUID NOT NULL,
    "lead_type" VARCHAR(50) NOT NULL,
    "sampling_rate" INTEGER NOT NULL,
    "sample_count" INTEGER NOT NULL,
    "signal_data" JSONB NOT NULL,
    "min_voltage_mv" DOUBLE PRECISION,
    "max_voltage_mv" DOUBLE PRECISION,

    CONSTRAINT "ecg_signal_data_pkey" PRIMARY KEY ("signal_id")
);

-- CreateTable
CREATE TABLE "ecg_analysis" (
    "analysis_id" UUID NOT NULL,
    "session_id" UUID NOT NULL,
    "heart_rate_bpm" INTEGER,
    "rhythm_type" VARCHAR(100),
    "pr_interval" DOUBLE PRECISION,
    "qrs_duration" DOUBLE PRECISION,
    "qt_interval" DOUBLE PRECISION,
    "qtc_interval_ms" DOUBLE PRECISION,
    "electrical_axis" DOUBLE PRECISION,
    "diagnosis" TEXT,

    CONSTRAINT "ecg_analysis_pkey" PRIMARY KEY ("analysis_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "users_phone_number_key" ON "users"("phone_number");

-- CreateIndex
CREATE UNIQUE INDEX "patients_user_id_key" ON "patients"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "patients_medical_record_number_key" ON "patients"("medical_record_number");

-- CreateIndex
CREATE UNIQUE INDEX "devices_serial_number_key" ON "devices"("serial_number");

-- CreateIndex
CREATE INDEX "ecg_sessions_patient_id_idx" ON "ecg_sessions"("patient_id");

-- CreateIndex
CREATE INDEX "ecg_sessions_device_id_idx" ON "ecg_sessions"("device_id");

-- CreateIndex
CREATE INDEX "ecg_sessions_created_by_idx" ON "ecg_sessions"("created_by");

-- CreateIndex
CREATE UNIQUE INDEX "ecg_signal_data_session_id_key" ON "ecg_signal_data"("session_id");

-- CreateIndex
CREATE INDEX "ecg_signal_data_session_id_idx" ON "ecg_signal_data"("session_id");

-- CreateIndex
CREATE UNIQUE INDEX "ecg_analysis_session_id_key" ON "ecg_analysis"("session_id");

-- CreateIndex
CREATE INDEX "ecg_analysis_session_id_idx" ON "ecg_analysis"("session_id");

-- AddForeignKey
ALTER TABLE "patients" ADD CONSTRAINT "patients_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("user_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ecg_sessions" ADD CONSTRAINT "ecg_sessions_patient_id_fkey" FOREIGN KEY ("patient_id") REFERENCES "patients"("patient_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ecg_sessions" ADD CONSTRAINT "ecg_sessions_device_id_fkey" FOREIGN KEY ("device_id") REFERENCES "devices"("device_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ecg_sessions" ADD CONSTRAINT "ecg_sessions_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "users"("user_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ecg_signal_data" ADD CONSTRAINT "ecg_signal_data_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "ecg_sessions"("session_id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ecg_analysis" ADD CONSTRAINT "ecg_analysis_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "ecg_sessions"("session_id") ON DELETE CASCADE ON UPDATE CASCADE;
