from __future__ import division
import numpy
import numpy.linalg as la




def have_cl():
    try:
        import pyopencl
        return True
    except:
        return False


if have_cl():
    import pyopencl as cl




class TestCL:
    disabled = not have_cl()

    def test_get_info(self):
        had_failures = [False]

        QUIRKS = [
                ("NVIDIA", [
                    (cl.Device, cl.device_info.PLATFORM),
                    ]),
                ]

        def find_quirk(quirk_list, cl_obj, info):
            for quirk_plat_name, quirks in quirk_list:
                if quirk_plat_name in platform.name:
                    for quirk_cls, quirk_info in quirks:
                        if (isinstance(cl_obj, quirk_cls)
                                and quirk_info == info):
                            return True

            return False

        def do_test(cl_obj, info_cls, func=None):
            if func is None:
                def func(info):
                    cl_obj.get_info(info)

            for info_name in dir(info_cls):
                if not info_name.startswith("_") and info_name != "to_string":
                    info = getattr(info_cls, info_name)

                    try:
                        func(info)
                    except:
                        print "failed get_info", type(cl_obj), info_name

                        if find_quirk(QUIRKS, cl_obj, info):
                            print "(known quirk for %s)" % platform.name
                        else:
                            had_failures[0] = True
                            raise

        for platform in cl.get_platforms():
            do_test(platform, cl.platform_info)

            for device in platform.get_devices():
                do_test(device, cl.device_info)

                ctx = cl.Context([device])
                do_test(ctx, cl.context_info)

                props = 0
                if (device.queue_properties
                        & cl.command_queue_properties.PROFILING_ENABLE):
                    profiling = True
                    props = cl.command_queue_properties.PROFILING_ENABLE
                queue = cl.CommandQueue(ctx,
                        properties=props)
                do_test(queue, cl.command_queue_info)

                prg = cl.create_program_with_source(ctx, """
                    __kernel void sum(__global float *a)
                    { a[get_global_id(0)] *= 2; }
                    """).build()
                do_test(prg, cl.program_info)
                do_test(prg, cl.program_build_info,
                        lambda info: prg.get_build_info(device, info))

                cl.unload_compiler() # just for the heck of it

                mf = cl.mem_flags
                n = 2000
                a_buf = cl.create_buffer(ctx, 0, n*4)

                do_test(a_buf, cl.mem_info)

                kernel = prg.sum
                do_test(kernel, cl.kernel_info)

                evt = kernel(queue, (n,), a_buf)
                do_test(evt, cl.event_info)

                if profiling:
                    evt.wait()
                    do_test(evt, cl.profiling_info,
                            lambda info: evt.get_profiling_info(info))

                if device.image_support:
                    if "NVIDIA" not in platform.name:
                        # Samplers are crashy in Nvidia's "conformant" CL release
                        smp = cl.Sampler(ctx, True,
                                cl.addressing_mode.CLAMP,
                                cl.filter_mode.NEAREST)
                        do_test(smp, cl.sampler_info)

                    img_format = cl.get_supported_image_formats(
                            ctx, cl.mem_flags.READ_ONLY, cl.mem_object_type.IMAGE2D)[0]

                    img = cl.create_image_2d(ctx, cl.mem_flags.READ_ONLY, img_format,
                            128, 128, 0)
                    do_test(img, cl.image_info,
                            lambda info: img.get_image_info(info))
                    img.image.depth

        if had_failures[0]:
            raise RuntimeError("get_info testing had errors")

    def test_invalid_kernel_names_cause_failures(self):
        for platform in cl.get_platforms():
            for device in platform.get_devices():
                ctx = cl.Context([device])
                prg = cl.create_program_with_source(ctx, """
                    __kernel void sum(__global float *a)
                    { a[get_global_id(0)] *= 2; }
                    """).build()

                try:
                    prg.sam
                    raise RuntimeError("invalid kernel name did not cause error")
                except AttributeError:
                    pass







if __name__ == "__main__":
    # make sure that import failures get reported, instead of skipping the tests.
    import pyopencl

    from py.test.cmdline import main
    main([__file__])
