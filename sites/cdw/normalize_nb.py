"""CDW → internal for notebooks (product_code NB)."""

from __future__ import annotations

import re

from core.schema.registry import empty_internal
from core.spec_lookup import extract_number, resolve_spec_field, spec_value, spec_list, split_and_filter_patterns
from core.units import length_to_in, weight_to_lb
from sites.cdw._common import cdw_payload, fill_identity_content, fill_item_dimensions_weight, parse_inch
from sites.cdw.spec_bindings import CDW_PROCESSOR_BINDINGS
from core.transforms import extract_bluetooth, normalize_capacity, extract_ethernet_speed

def normalize_cdw_nb(raw: dict) -> dict:
    cdw = cdw_payload(raw)
    specs = cdw.get("specs") or {}
    internal = empty_internal("NB")

    fill_identity_content(internal, raw=raw, cdw=cdw, specs=specs, spec_value=spec_value)

    #identity and content dict get from cdw\_common fill_identity_content()

    # processor
    internal["processor"]["brand"] = spec_value(specs, "Processor", "Processor Brand")
    internal["processor"]["model"] = " ".join(p for p in [
            spec_value(specs, "Processor", "Processor Type"),
            spec_value(specs, "Processor", "Processor Number"),
        ] if p ).strip()
    cores_cfg = CDW_PROCESSOR_BINDINGS["cores"]
    internal["processor"]["cores"] = resolve_spec_field(specs, cores_cfg["paths"], parse=cores_cfg.get("parse"), prefer_keywords=cores_cfg.get("prefer_keywords"))
    threads_cfg = CDW_PROCESSOR_BINDINGS["threads"]
    internal["processor"]["threads"] = resolve_spec_field(specs, threads_cfg["paths"], parse=threads_cfg.get("parse"), prefer_keywords=threads_cfg.get("prefer_keywords"))
    internal["processor"]["clock_ghz"] = extract_number(spec_value(specs, "Processor", "Clock Speed"))
    internal["processor"]["max_clock_ghz"] = extract_number(spec_value(specs, "Processor", "Max Turbo Speed"))
    internal["processor"]["cache_mb"] = extract_number(spec_value(specs, "Memory", "Cache Memory Installed"))
    internal["processor"]["family"] = spec_value(specs, "Processor", "Processor Type")
    internal["processor"]["number"] = spec_value(specs, "Processor", "Processor Number")
    internal["processor"]["generation"] = spec_value(specs, "Processor", "Processor Generation")
    internal["processor"]["platform_technology"] = spec_value(specs, "Processor", "Platform Technology")
    internal["processor"]["ai_processor_technology"] = spec_value(specs, "Processor", "AI Processor Technology")

    # memory
    internal["memory"]["type"] = split_and_filter_patterns(spec_value(specs, "Memory", "Memory Technology"), exclude_patterns=["GDDR* SDRAM", ])
    mem_match = re.search(r"\d+", spec_value(specs, "Memory", "RAM Installed"))
    internal["memory"]["capacity_gb"] = mem_match.group(0) if mem_match else ""
    max_mem_match = re.search(r"\d+",spec_value(specs, "Memory", "Max Memory Supported"))
    internal["memory"]["max_capacity_gb"] = (max_mem_match.group(0) if max_mem_match else "")
    internal["memory"]["speed_mhz"] = extract_number(spec_value(specs, "Memory", "Memory Speed"))
    internal["memory"]["rated_speed_mhz"] = extract_number(spec_value(specs, "Memory", "Rated Memory Speed"))
    internal["memory"]["configuration_features"] = spec_value(specs, "Memory", "Configuration Features")
    internal["memory"]["slots"] = spec_value(specs, "Memory", "Memory Slots")
    internal["memory"]["expansion_slots"] = (spec_value(specs, "Memory", "Available Memory Slots") or spec_value(specs, "Expansion Slots", "Slots"))

    # storage
    internal["storage"]["type"] = spec_value(specs, "Storage", "Storage Type")
    internal["storage"]["capacity_gb"] = normalize_capacity(spec_value(specs, "Storage", "Hard Drive Capacity"), "GB")
    internal["storage"]["ssd_form_factor"] = spec_value(specs, "Storage", "SSD Form Factor")
    internal["storage"]["optical_drive"] = spec_value(specs, "Storage", "Optical Drive Type")
    internal["storage"]["interface"] = spec_value(specs, "Storage", "Hard Drive Interface")
    internal["storage"]["features"] = spec_value(specs, "Storage", "Hard Drive Features")

    # graphics
    internal["graphics"]["type"] = spec_value(specs, "Display & Graphics", "Discrete Graphics Processor")
    internal["graphics"]["processor"]["model"] = spec_list(specs, "Display & Graphics", "Graphics Controller Model")
    internal["graphics"]["processor"]["series"] = spec_value(specs, "Display & Graphics", "Graphics Processor Series")
    internal["graphics"]["vram_gb"] = normalize_capacity(spec_value(specs, "Video", "Installed Size"), "GB")

    # display
    internal["display"]["size_in"] = extract_number(spec_value(specs, "Display & Graphics", "Screen Size"))
    internal["display"]["panel"] = spec_value(specs, "Display & Graphics", "TFT Technology")
    internal["display"]["resolution"] = spec_value(specs, "Display & Graphics", "Native Resolution")
    internal["display"]["features"] = spec_list(specs, "Display & Graphics", "Features")
    internal["display"]["brightness_cdm2"] = extract_number(spec_value(specs, "Display & Graphics", "Display Image Brightness"))
    internal["display"]["refresh_rate_hz"] = extract_number(spec_value(specs, "Display & Graphics", "V-Sync Rate at Max Res."))
    internal["display"]["horizontal_viewing_angle"] = spec_value(specs, "Display & Graphics", "Horizontal Viewing Angle")
    internal["display"]["vertical_viewing_angle"] = spec_value(specs, "Display & Graphics", "Vertical Viewing Angle")
    internal["display"]["pixel_density_ppl"] = extract_number(spec_value(specs, "Display & Graphics", "Pixel Density (ppi)"))
    internal["display"]["privacy_technology"] = spec_value(specs, "Display & Graphics", "Privacy Technology")
    internal["display"]["widescreen"] = spec_value(specs, "Display & Graphics", "Widescreen Display")
    internal["display"]["touchscreen"] = spec_value(specs, "Display & Graphics", "Touchscreen")

    # audio
    internal["audio"]["input_type"] = spec_value(specs, "Audio", "Audio Input Type")
    internal["audio"]["compliant_standards"] = spec_list(specs, "Audio", "Compliant Standards")
    internal["audio"]["output_types"] = spec_list(specs, "Product Information", "Output Type")
    internal["audio"]["output_features"] = spec_value(specs, "Product Information", "Audio Output Features")

    #camera
    internal["camera"]["webcam"] = spec_value(specs, "Camera", "Webcam")
    internal["camera"]["front_camera_resolution"] = spec_list(specs, "Camera", "Front Camera Resolution")
    internal["camera"]["front_camera_video_resolution"] = spec_list(specs, "Camera", "Front Camera Video Resolution")
    internal["camera"]["image_sensor_type"] = spec_value(specs, "Camera", "Image Sensor Type")
    internal["camera"]["frame_rate_fps"] = extract_number(spec_value(specs, "Camera", "Frame Rate"))
    internal["camera"]["pixel"] = spec_value(specs, "Technical Information", "Camera Resolution")

    # io
    internal["io"]["hdmi_ports"] = spec_value(specs, "Connectivity", "HDMI Ports")
    internal["io"]["usb_3_ports"] = spec_value(specs, "Connectivity", "USB 3.0 Ports")
    internal["io"]["usb_c_ports"] = spec_value(specs, "Connectivity", "USB Type-C Ports")
    internal["io"]["usb_c_features"] = spec_list(specs, "Connectivity", "USB-C Features")
    internal["io"]["flash_memory"] = spec_list(specs, "Memory", "Supported Flash Memory")
    internal["io"]["ports"] = spec_list(specs, "Connectivity", "Interfaces")
    internal["io"]["input_device_features"] = spec_list(specs, "Product Information", "Input Device Features")
    internal["io"]["keyboard_backlight"] = spec_value(specs, "Product Information", "Keyboard Backlight")

    # power
    internal["power"]["battery"]["capacity"] = spec_value(specs, "Power", "Battery Capacity")
    internal["power"]["battery"]["cells"] = extract_number(spec_value(specs, "Power", "Battery Cells"))
    internal["power"]["battery"]["chemistry"] = spec_value(specs, "Power", "Battery Chemistry")
    internal["power"]["frequency"] = spec_value(specs, "Power", "Frequency")
    internal["power"]["power_watt"] = extract_number(spec_value(specs, "Power", "Power Provided"))
    internal["power"]["voltage"] = spec_value(specs, "Power", "Provided Voltage")
    internal["power"]["voltage_required"] = spec_value(specs, "Power", "Required Voltage")
    internal["power"]["battery_life_hour"] = extract_number(spec_value(specs, "Power", "Battery Run Time (Up To)"))

    # network
    internal["network"]["wifi"] = spec_value(specs, "Network & Communication", "Wireless LAN").replace(", ","").replace("Bluetooth", "")
    internal["network"]["bluetooth"] = spec_value(specs,"Network & Communication", "Bluetooth") or extract_bluetooth(spec_value(specs, "Network & Communication", "Data Link Protocols"))
    internal["network"]["wireless_nic"] = spec_value(specs, "Network & Communication", "Wireless NIC")
    internal["network"]["ethernet_speed"] = extract_ethernet_speed(spec_value(specs, "Network & Communication", "Wired Protocol"))
    internal["network"]["features"] = spec_list(specs, "Network & Communication", "Features")

    # software
    internal["software"]["os"] = spec_value(specs, "Software", "Operating System")
    # platform = spec_value(specs, "Product Information", "Platform Supported")
    # if not platform:
    #     platform = spec_value(specs, "Software", "Operating System Platform")
    # internal["software"]["platform"] = platform
    internal["software"]["platform"] = (spec_value(specs, "Product Information", "Platform Supported") or spec_value(specs, "Software", "Operating System Platform") )
    internal["software"]["types"] = spec_list(specs, "Software", "Software Type")

    # technical
    internal["technical"]["embedded_security"] = spec_value(specs, "Technical Information", "Embedded Security")
    internal["technical"]["finger_pinter_reader"] = spec_value(specs, "Technical Information", "Finger Print Reader")
    internal["technical"]["max_operating_temperature_degree"] = extract_number(spec_value(specs, "Technical Information", "Max Operating Temperature"))
    internal["technical"]["min_operating_temperature_degree"] = extract_number(spec_value(specs, "Technical Information", "Min Operating Temperature"))
    internal["technical"]["operating_humidity"] = spec_value(specs, "Technical Information", "Operating Humidity")
    internal["technical"]["rugged"] = spec_value(specs, "Technical Information", "Rugged")
    internal["technical"]["sensor_type"] = spec_list(specs, "Technical Information", "Sensor Type")
    internal["technical"]["security_slot_type"] = spec_value(specs, "Product Information", "Security Slot Type")
    internal["technical"]["service_activation"] = spec_value(specs, "Product Information", "Service Activation")
    internal["technical"]["theft_protection"] = spec_value(specs, "Product Information", "Theft Protection")
    internal["technical"]["bundled_services"] = spec_value(specs, "Scanning", "Bundled Services")

    # certification
    internal["certification"]["compliant_standards"] = spec_list(specs, "Certifications & Listings", "Compliant Standards")
    internal["certification"]["energy_star_certified"] = spec_value(specs, "Certifications & Listings", "ENERGY STAR Certified")
    internal["certification"]["epeat_compliant"] = spec_value(specs, "Certifications & Listings", "EPEAT Compliant")
    internal["certification"]["epeat_level"] = spec_value(specs, "Certifications & Listings", "EPEAT Level").replace(" ", "").replace("EPEAT", "")
    internal["certification"]["tco_certified"] = spec_value(specs, "Certifications & Listings", "TCO Certified")

    #included_items
    acc = spec_value(specs, "Included Items", "Included Accessories")
    if acc:
        internal["included_items"] = [p.strip() for p in re.split(r"[,;]", acc) if p.strip()]

    # physical
    internal["physical"]["packaged_qty"] = spec_value(specs, "Product Information", "Packaged Quantity")
    internal["physical"]["material"] = spec_value(specs, "Physical Characteristics", "Case Material")
    internal["physical"]["color"] = spec_value(specs, "Physical Characteristics", "Color")
    internal["physical"]["color_category"] = spec_value(specs, "Physical Characteristics", "Color Category")
    fill_item_dimensions_weight(internal, specs, spec_value=spec_value, length_to_in=length_to_in, weight_to_lb=weight_to_lb,)

    return internal
