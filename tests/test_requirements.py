from firmware_validation_agent.requirements import load_hardware_spec


def test_load_hardware_spec_parses_registers_and_requirements():
    spec = load_hardware_spec("examples/optical_module_requirements.yaml")

    assert spec.module_name == "synthetic-sipho-optical-module"
    assert spec.registers["module_temp_c"].address == 0x10
    assert spec.registers["laser_bias_ma"].maximum == 120.0
    assert len(spec.requirements) == 7
    assert spec.requirements[0].id == "REQ-001"
