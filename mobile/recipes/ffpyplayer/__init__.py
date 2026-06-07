from os.path import join

from pythonforandroid.recipe import PyProjectRecipe, Recipe


class FFPyPlayerRecipe(PyProjectRecipe):
    """Receita local que substitui a oficial do python-for-android.

    A única diferença: antes de compilar, remove um bloco de bindings Cython
    mortos (declarações da API AVFFT, de libavcodec/avfft.h) que não são
    usados em lugar nenhum do ffpyplayer — confirmado via busca no código-fonte
    do projeto. Esse header foi removido do FFmpeg 5.0+ (a receita oficial do
    ffmpeg usa 8.0.1), então só de existir essas declarações o build quebra com
    "fatal error: 'libavcodec/avfft.h' file not found", mesmo sem nada usá-las.
    """

    version = 'v4.5.1'
    url = 'https://github.com/matham/ffpyplayer/archive/{version}.zip'
    depends = ['python3', 'sdl2', 'ffmpeg']
    patches = ["setup.py.patch"]
    opt_depends = ['openssl', 'ffpyplayer_codecs']

    def get_recipe_env(self, arch, with_flags_in_cc=True):
        env = super().get_recipe_env(arch)

        build_dir = Recipe.get_recipe('ffmpeg', self.ctx).get_build_dir(arch.arch)
        env["FFMPEG_INCLUDE_DIR"] = join(build_dir, "include")
        env["FFMPEG_LIB_DIR"] = join(build_dir, "lib")

        env["SDL_INCLUDE_DIR"] = join(self.ctx.bootstrap.build_dir, 'jni', 'SDL', 'include')
        env["SDL_LIB_DIR"] = join(self.ctx.bootstrap.build_dir, 'libs', arch.arch)

        env["USE_SDL2_MIXER"] = '1'

        sdl2_mixer_recipe = self.get_recipe('sdl2_mixer', self.ctx)
        env["SDL2_MIXER_INCLUDE_DIR"] = sdl2_mixer_recipe.get_include_dirs(arch)[0]

        env['NDKPLATFORM'] = "NOTNONE"
        env['LIBLINK'] = 'NOTNONE'

        if 'ffpyplayer_codecs' not in self.ctx.recipe_build_order:
            env["CONFIG_POSTPROC"] = '0'

        return env

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)

        pxi_path = join(self.get_build_dir(arch.arch), 'ffpyplayer', 'includes', 'ffmpeg.pxi')
        with open(pxi_path, encoding='utf-8') as f:
            source = f.read()

        dead_avfft_block = (
            '    extern from "libavcodec/avfft.h" nogil:\n'
            '        enum RDFTransformType:\n'
            '            DFT_R2C,\n'
            '            IDFT_C2R,\n'
            '            IDFT_R2C,\n'
            '            DFT_C2R,\n'
            '        struct RDFTContext:\n'
            '            pass\n'
            '        void av_rdft_end(RDFTContext *)\n'
            '        RDFTContext *av_rdft_init(int, RDFTransformType)\n'
            '        void av_rdft_calc(RDFTContext *, FFTSample *)\n'
            '\n'
        )
        if dead_avfft_block not in source:
            raise Exception(
                'Bloco de bindings avfft.h não encontrado em ffmpeg.pxi — '
                'o código-fonte do ffpyplayer mudou; revise o patch em '
                'mobile/recipes/ffpyplayer/__init__.py'
            )

        with open(pxi_path, 'w', encoding='utf-8') as f:
            f.write(source.replace(dead_avfft_block, '', 1))


recipe = FFPyPlayerRecipe()
